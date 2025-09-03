from pathlib import Path
import shutil
import json
from markdown2 import Markdown
from jinja2 import Environment, FileSystemLoader
import datetime
import random
import re
import xml.etree.ElementTree as ET
from datetime import datetime as dt


def setup_jinja():
    """Set up Jinja environment"""
    env = Environment(loader=FileSystemLoader("src/templates"), autoescape=True)

    # Add current year to all templates
    env.globals["now"] = type("", (), {"year": datetime.datetime.now().year})()

    # Random number for cache busting
    env.globals["cache_bust"] = str(random.randint(0, 1000000))

    # Add is_homepage flag
    env.globals["is_homepage"] = False

    return env


def convert_markdown_to_html(
    markdown_file_path, metadata=None, output_dir=Path("blog")
):
    """
    Convert a markdown file to HTML using markdown2 and save it with proper HTML structure.

    Args:
        markdown_file_path (str): Path to the markdown file
        metadata (dict, optional): Post metadata including title, description, etc.
    """
    markdowner = Markdown(extras=["fenced-code-blocks", "latex", "tables"])
    env = setup_jinja()
    template = env.get_template("blog-post.html")

    # Read markdown and convert to HTML
    with open(markdown_file_path) as f:
        content = f.read()
        html_content = markdowner.convert(content)

        # Pre-processing steps
        html_content = re.sub(
            r'(<math[^>]*display="block"[^>]*>.*?</math>)',
            r'<div class="math-container">\1</div>',
            html_content,
            flags=re.DOTALL,
        )

    # Render template
    html = template.render(
        title=metadata.get("name", "Blog Post") if metadata else "Blog Post",
        description=metadata.get("description", "") if metadata else "",
        content=html_content,
        static_prefix="../static",
        root_prefix="..",
        id=metadata.get("id", "") if metadata else "",
    )

    # Use the URL from metadata for the filename, fallback to original name if no metadata
    if metadata and "url" in metadata:
        html_filename = f"{metadata['url']}.html"
    else:
        html_filename = Path(markdown_file_path).name.replace(".md", ".html")

    html_path = output_dir / html_filename
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return html


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
    """Copy static files to the publish directory"""

    # Copy static directory from src
    if (src_dir / "static").exists():
        shutil.copytree(src_dir / "static", publish_dir / "static")

    # Copy blog images
    if (src_dir / "blog/img").exists():
        shutil.copytree(src_dir / "blog/img", publish_dir / "blog/img")

    # Favicon ico goes in the root
    if (src_dir / "favicon.ico").exists():
        shutil.copy(src_dir / "favicon.ico", publish_dir / "favicon.ico")


def generate_blog_index(blog_posts, publish_dir, src_dir):
    """Generate the blog index page listing all posts"""
    env = setup_jinja()
    template = env.get_template("blog-index.html")

    sorted_posts = sorted(blog_posts, key=lambda x: x.get("date", ""), reverse=True)

    # Render template
    html = template.render(
        title="Blog",
        description="Hot takes, sorted chronologically",
        posts=sorted_posts,
        static_prefix="../static",
        root_prefix="..",
    )

    # Write the generated index page
    with open(publish_dir / "blog/index.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_home(publish_dir):
    """Generate the homepage"""
    env = setup_jinja()
    template = env.get_template("home.html")

    # Set is_homepage to True for the homepage
    env.globals["is_homepage"] = True

    html = template.render(
        title="vtasca.dev",
        description="Hot takes, ordered chronologically",
        static_prefix="static",
        root_prefix=".",
    )

    with open(publish_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_rss_feed(blog_posts, publish_dir):
    """Generate the RSS feed XML file"""
    env = setup_jinja()
    template = env.get_template("rss.xml")

    # Sort posts by last edited time, newest first
    sorted_posts = sorted(
        blog_posts, key=lambda x: x.get("last_edited_time", ""), reverse=True
    )

    # Render template
    xml = template.render(posts=sorted_posts, now=datetime.datetime.now())

    # Write the RSS feed
    with open(publish_dir / "blog/rss.xml", "w", encoding="utf-8") as f:
        f.write(xml)


def generate_contact(publish_dir):
    """Generate the contact page"""
    env = setup_jinja()
    template = env.get_template("contact.html")

    html = template.render(
        title="Contact",
        description="It's almost like shouting into the void",
        static_prefix="static",
        root_prefix=".",
    )

    with open(publish_dir / "contact.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_sitemap(publish_dir, src_dir, blog_posts):
    """Generate sitemap.xml"""

    sitemap = """
                <?xml version='1.0' encoding='utf-8'?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                """

    # Create mapping between templates and HTML files
    template_to_html_mapping = {
        "home.html": "index.html",
        "contact.html": "contact.html",
        "blog-index.html": "blog/index.html",
    }

    # Get all HTML files recursively from publish_dir
    html_files = []
    for path in publish_dir.rglob("*.html"):
        # Convert to relative path from publish_dir
        rel_path = path.relative_to(publish_dir)
        html_files.append(str(rel_path))

    # Get all template files
    templates = []
    for path in (src_dir / "templates").rglob("*.html"):
        templates.append(path.relative_to(src_dir / "templates"))

    # Create reverse mapping from HTML files to templates
    html_to_template_mapping = {}
    for template, html_file in template_to_html_mapping.items():
        html_to_template_mapping[html_file] = template

    # Add blog posts to the mapping
    for post in blog_posts:
        if "url" in post:
            html_file = f"blog/{post['url']}.html"
            # Blog posts use the blog-post.html template
            html_to_template_mapping[html_file] = "blog-post.html"

        # Get last modified time for each file by checking the source template
    last_modified = {}
    for html_file in html_files:
        if html_file in html_to_template_mapping:
            template_name = html_to_template_mapping[html_file]
            template_path = src_dir / "templates" / template_name
            
            if template_path.exists():
                # Use template modification time for static pages
                last_modified[html_file] = dt.fromtimestamp(
                    template_path.stat().st_mtime
                ).strftime("%Y-%m-%dT%H:%M:%S")
            else:
                # Fallback to HTML file modification time
                html_path = publish_dir / html_file
                if html_path.exists():
                    last_modified[html_file] = dt.fromtimestamp(
                        html_path.stat().st_mtime
                    ).strftime("%Y-%m-%dT%H:%M:%S")
        else:
            # For files not in mapping, use HTML file modification time
            html_path = publish_dir / html_file
            if html_path.exists():
                last_modified[html_file] = dt.fromtimestamp(
                    html_path.stat().st_mtime
                ).strftime("%Y-%m-%dT%H:%M:%S")

    # Add each URL to sitemap with lastmod
    for html_file in html_files:
        # Clean up the URL: remove index.html and .html suffixes
        clean_url = html_file
        if clean_url.endswith("index.html"):
            clean_url = clean_url[:-10]  # Remove "index.html"
        elif clean_url.endswith(".html"):
            clean_url = clean_url[:-5]   # Remove ".html"
        
        url = f"<url>\n<loc>https://vtasca.dev/{clean_url}</loc>\n"
        if html_file in last_modified:
            url += f"<lastmod>{last_modified[html_file]}</lastmod>\n"
        url += "</url>\n"
        sitemap += url

    sitemap += "</urlset>"

    # Write sitemap file
    with open(publish_dir / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap.strip())


if __name__ == "__main__":
    # Set up directories
    publish_dir, src_dir = set_up_directories()

    # Copy static files
    copy_files(publish_dir, src_dir)

    # Generate blog posts
    with open(src_dir / "blog_metadata.json", "r") as f:
        blog_posts = json.load(f)

    for post in blog_posts:
        convert_markdown_to_html(
            Path("src/blog/md") / (post["id"] + ".md"),
            metadata=post,
            output_dir=publish_dir / "blog",
        )

    # Generate other pages
    generate_home(publish_dir)
    generate_blog_index(blog_posts, publish_dir, src_dir)
    generate_rss_feed(blog_posts, publish_dir)
    generate_contact(publish_dir)
    generate_sitemap(publish_dir, src_dir, blog_posts)
