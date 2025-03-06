from pathlib import Path
import shutil
import json
from markdown2 import Markdown

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


def convert_markdown_to_html(markdown_file_path, metadata=None, output_dir=Path("blog")):
    """
    Convert a markdown file to HTML using markdown2 and save it with proper HTML structure.

    Args:
        markdown_file_path (str): Path to the markdown file
        metadata (dict, optional): Post metadata including title, description, etc.
    """
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

def set_up_directories():
    """Create and clean the publish directory structure and return the publish and src directories"""
    publish_dir = Path("published")
    src_dir = Path("src")
    
    # Remove existing publish directory if it exists
    if publish_dir.exists():
        shutil.rmtree(publish_dir)
    
    # Create fresh directory structure
    publish_dir.mkdir()
    (publish_dir / "blog").mkdir()
    
    return publish_dir, src_dir

def copy_files(publish_dir, src_dir):
    """Copy static files and index.html to the publish directory"""

    # Copy static directory from src
    if (src_dir / "static").exists():
        shutil.copytree(src_dir / "static", publish_dir / "static")
    
    # Copy index.html from src
    if (src_dir / "index.html").exists():
        shutil.copy2(src_dir / "index.html", publish_dir)

    # Copy blog.html from src
    if (src_dir / "blog.html").exists():
        shutil.copy2(src_dir / "blog.html", publish_dir)

    # Copy blog images
    if (src_dir / "blog/img").exists():
        shutil.copytree(src_dir / "blog/img", publish_dir / "blog/img")



if __name__ == "__main__":
    
    publish_dir, src_dir = set_up_directories()

    copy_files(publish_dir, src_dir)

    with open(src_dir / "blog_metadata.json", "r") as f:
        blog_posts = json.load(f)

    for post in blog_posts:
        convert_markdown_to_html(Path("src/blog/md") / (post['id'] + ".md"), metadata=post, output_dir=publish_dir / "blog")
