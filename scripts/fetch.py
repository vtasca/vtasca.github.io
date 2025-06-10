from notion_client import Client
from notion2md.exporter.block import MarkdownExporter
import os
from pathlib import Path
import json
import shutil
import zipfile
import re
import unicodedata
import requests
from process_svg import process_svg

from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

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

def extract_blog_metadata(posts, output_dir='src', filename='blog_metadata.json'):
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

        def get_text_content(prop_name, prop_type="rich_text"):
            prop = properties.get(prop_name, {}).get(prop_type, [])
            return prop[0].get("plain_text", "") if prop else ""

        # Get the image URL if it exists
        image_prop = properties.get("Image", {}).get("files", [])
        image_url = image_prop[0].get("file", {}).get("url") if image_prop else None

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
    with open(Path(output_dir) / filename, "w", encoding="utf-8") as f:
        json.dump(blog_data, f, ensure_ascii=False, indent=2)

    return blog_data

def export_markdown(block_id, output_dir='src'):
    # Only create directories if they don't exist - don't delete them
    Path(output_dir + "/blog/md").mkdir(exist_ok=True, parents=True)
    Path(output_dir + "/blog/img").mkdir(exist_ok=True, parents=True)

    # Get the post metadata to check for header image
    notion = Client(auth=NOTION_TOKEN)
    post = notion.pages.retrieve(page_id=block_id)
    properties = post["properties"]
    
    # Get the image URL if it exists
    image_prop = properties.get("Image", {}).get("files", [])
    image_url = image_prop[0].get("file", {}).get("url") if image_prop else None
    
    # Download header image if it exists
    if image_url:
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            # Extract file extension from URL, default to .png if not found
            image_ext = Path(image_url.split('?')[0]).suffix or '.png'
            # Save the image with the post ID as filename
            image_path = Path(output_dir + "/blog/img") / f"{block_id}{image_ext}"
            with open(image_path, 'wb') as f:
                f.write(image_response.content)
            
            # Process SVG files if the image is an SVG
            if image_ext.lower() == '.svg':
                process_svg(str(image_path), '#e0e0e0')

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
                           lambda m: f'![{m.group(1)}](img/{Path(m.group(2)).name})', 
                           content)

        # Move the markdown file to md directory with updated content
        md_destination = Path(output_dir + "/blog/md") / markdown_path.name
        with open(md_destination, 'w', encoding='utf-8') as f:
            f.write(content)

        # Move all images to published/img directory
        for img_path in image_files:
            shutil.move(str(img_path), Path(output_dir + "/blog/img") / img_path.name)

        # Clean up
        shutil.rmtree("markdown_zip_container")
        shutil.rmtree("temp_extract")

    except PermissionError:
        print(
            "Could not access the files. Please ensure they're not open in another program."
        )
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Get all blog posts
    all_blog_posts = get_database_entries(DATABASE_ID)

    extract_blog_metadata(all_blog_posts, output_dir="src", filename="blog_metadata.json")

    # Clean directories once before processing all posts
    if Path("src/blog/md").exists():
        shutil.rmtree("src/blog/md", ignore_errors=True)
    if Path("src/blog/img").exists():
        shutil.rmtree("src/blog/img", ignore_errors=True)
    

    # Load blog metadata from JSON file
    with open("src/blog_metadata.json", "r") as f:
        blog_posts = json.load(f)

    for post in blog_posts:
        export_markdown(post["id"])