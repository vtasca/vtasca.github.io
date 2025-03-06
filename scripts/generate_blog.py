import os
import zipfile
import shutil
from pathlib import Path
import json
import unicodedata
import re
from datetime import datetime

from notion2md.exporter.block import MarkdownExporter
from notion_client import Client
from markdown2 import Markdown
from dotenv import load_dotenv


load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

def setup_publish_directory():
    """Create and clean the publish directory structure"""
    publish_dir = Path("published")
    src_dir = Path("src")
    
    # Remove existing publish directory if it exists
    if publish_dir.exists():
        shutil.rmtree(publish_dir)
    
    # Create fresh directory structure
    publish_dir.mkdir()
    (publish_dir / "blog").mkdir()
    (publish_dir / "img").mkdir()
    
    # Copy static directory from src
    if (src_dir / "static").exists():
        shutil.copytree(src_dir / "static", publish_dir / "static")
    
    # Copy index.html from src
    if (src_dir / "index.html").exists():
        shutil.copy2(src_dir / "index.html", publish_dir)
    
    return publish_dir

def clean_root_directory():
    shutil.rmtree("md")
    shutil.rmtree("blog")


def get_database_entries(database_id):
    """
    Fetch all pages from a Notion database
    Returns the full results list containing all page data
    """
    results = []

    notion = Client(auth=NOTION_TOKEN)

    # Query the database
    response = notion.databases.query(database_id=database_id)

    # Add the first set of results
    results.extend(response["results"])

    # Continue fetching if there are more results
    while response.get("has_more"):
        response = notion.databases.query(
            database_id=database_id, start_cursor=response["next_cursor"]
        )
        results.extend(response["results"])

    return results


def slugify(value, allow_unicode=False):
    """Slugify!"""
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def extract_blog_metadata(posts, filename="blog_metadata.json"):
    """
    Extract relevant information from blog posts and format it for JSON export
    Only includes posts where published=True
    """
    blog_data = []

    for post in posts:
        properties = post["properties"]

        # Skip unpublished posts
        if not properties.get("Published Status", {}).get("checkbox", False):
            continue

        # ... existing code ...
        def get_text_content(prop_name, prop_type="rich_text"):
            prop = properties.get(prop_name, {}).get(prop_type, [])
            return prop[0].get("plain_text", "") if prop else ""

        metadata = {
            "id": post["id"],
            "name": get_text_content("Name", "title"),
            "url": slugify(get_text_content("Name", "title")),
            "description": get_text_content("Description"),
            "tags": [
                tag["name"]
                for tag in properties.get("Tags", {}).get("multi_select", [])
            ],
            "published": True,  # We know it's True since we filtered
            "created_time": post.get("created_time"),
            "last_edited_time": post.get("last_edited_time"),
        }

        blog_data.append(metadata)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(blog_data, f, ensure_ascii=False, indent=2)

    return blog_data


# --- Create markdown files


def export_markdown(block_id, publish_dir):
    # Create temporary directories if they don't exist
    Path("md").mkdir(exist_ok=True)

    MarkdownExporter(
        block_id=block_id, output_path="markdown_zip_container", download=True
    ).export()

    try:
        # Find the zip file in the container directory
        zip_path = list(Path("markdown_zip_container").glob("*.zip"))[0]

        # Unzip the file
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall("temp_extract")

        # Find the markdown file and images
        markdown_path = list(Path("temp_extract").rglob("*.md"))[0]
        image_files = (
            list(Path("temp_extract").rglob("*.png"))
            + list(Path("temp_extract").rglob("*.jpg"))
            + list(Path("temp_extract").rglob("*.jpeg"))
        )

        # Read and modify the markdown content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Update image paths to use ../img/
            content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', 
                           lambda m: f'![{m.group(1)}](../img/{Path(m.group(2)).name})', 
                           content)

        # Move the markdown file to md directory with updated content
        md_destination = Path("md") / markdown_path.name
        with open(md_destination, 'w', encoding='utf-8') as f:
            f.write(content)

        # Move all images to published/img directory
        for img_path in image_files:
            shutil.move(str(img_path), publish_dir / "img" / img_path.name)

        # Clean up
        shutil.rmtree("markdown_zip_container")
        shutil.rmtree("temp_extract")

    except PermissionError:
        print(
            "Could not access the files. Please ensure they're not open in another program."
        )
    except Exception as e:
        print(f"An error occurred: {str(e)}")


# --- Markdown to html
def get_html_template():
    """
    Returns the base HTML template for blog posts.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | vtasca.dev</title>
    <meta name="description" content="{description}">
    <link rel="stylesheet" href="../static/styles.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    
    <link rel="stylesheet" href="https://unpkg.com/highlightjs-copy/dist/highlightjs-copy.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://unpkg.com/highlightjs-copy/dist/highlightjs-copy.min.js"></script>
    <script>
        hljs.highlightAll();
        hljs.addPlugin(new CopyButtonPlugin());
    </script>
</head>
<body>
    <header>
        <nav>
            <a href="../">Home</a>
        </nav>
    </header>

    <main>
        <article>
            {content}
        </article>
    </main>

    <footer>
        <!-- Add your footer content -->
    </footer>

    <script src="../static/core.js"></script>
</body>
</html>
"""


def convert_markdown_to_html(markdown_file_path, metadata=None, output_dir=Path("static/blog")):
    """
    Convert a markdown file to HTML using markdown2 and save it with proper HTML structure.

    Args:
        markdown_file_path (str): Path to the markdown file
        metadata (dict, optional): Post metadata including title, description, etc.
    """
    Path("blog").mkdir(exist_ok=True)
    markdowner = Markdown(extras=["fenced-code-blocks", "latex"])

    # Read markdown and convert to HTML
    with open(markdown_file_path) as f:
        content = f.read()
        html_content = markdowner.convert(content)

    # Get the template
    template = get_html_template()

    # Prepare template variables
    template_vars = {
        "title": metadata.get("name", "Blog Post") if metadata else "Blog Post",
        "description": metadata.get("description", "") if metadata else "",
        "content": html_content,
    }

    # Insert content into template
    final_html = template.format(**template_vars)

    # Use the URL from metadata for the filename, fallback to original name if no metadata
    if metadata and "url" in metadata:
        html_filename = f"{metadata['url']}.html"
    else:
        html_filename = Path(markdown_file_path).name.replace(".md", ".html")

    html_path = output_dir / html_filename
    with open(html_path, "w") as f:
        f.write(final_html)

    return final_html


if __name__ == "__main__":
    publish_dir = setup_publish_directory()

    # Get all blog posts
    all_blog_posts = get_database_entries(DATABASE_ID)

    extract_blog_metadata(all_blog_posts, filename=publish_dir / "blog_metadata.json")

    # Load blog metadata from JSON file
    with open(publish_dir / "blog_metadata.json", "r") as f:
        blog_posts = json.load(f)

    for post in blog_posts:
        export_markdown(post["id"], publish_dir)
        convert_markdown_to_html(f"md/{post['id']}.md", metadata=post, output_dir=publish_dir / "blog")

    clean_root_directory()
