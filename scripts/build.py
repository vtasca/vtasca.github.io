from pathlib import Path
import shutil
import json
from markdown2 import Markdown
from jinja2 import Environment, FileSystemLoader
import datetime
import random
def setup_jinja():
    """Set up Jinja environment"""
    env = Environment(
        loader=FileSystemLoader('src/templates'),
        autoescape=True
    )
    
    # Add current year to all templates
    env.globals['now'] = type('', (), {'year': datetime.datetime.now().year})()

    # Random number for cache busting
    env.globals['cache_bust'] = str(random.randint(0, 1000000))
    
    # Add is_homepage flag
    env.globals['is_homepage'] = False
    
    return env

def convert_markdown_to_html(markdown_file_path, metadata=None, output_dir=Path("blog")):
    """
    Convert a markdown file to HTML using markdown2 and save it with proper HTML structure.

    Args:
        markdown_file_path (str): Path to the markdown file
        metadata (dict, optional): Post metadata including title, description, etc.
    """
    markdowner = Markdown(extras=["fenced-code-blocks", "latex"])
    env = setup_jinja()
    template = env.get_template("blog-post.html")

    # Read markdown and convert to HTML
    with open(markdown_file_path) as f:
        content = f.read()
        html_content = markdowner.convert(content)

    # Render template
    html = template.render(
        title=metadata.get("name", "Blog Post") if metadata else "Blog Post",
        description=metadata.get("description", "") if metadata else "",
        content=html_content,
        static_prefix="../static",
        root_prefix=".."
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


def generate_blog_index(blog_posts, publish_dir, src_dir):
    """Generate the blog index page listing all posts"""
    env = setup_jinja()
    template = env.get_template("blog-index.html")

    sorted_posts = sorted(blog_posts, key=lambda x: x.get('date', ''), reverse=True)

    # Render template

    html = template.render(
        title="Blog",
        description="Hot takes, sorted chronologically",
        posts=sorted_posts,
        static_prefix="../static",
        root_prefix=".."
    )

    # Write the generated index page
    with open(publish_dir / "blog/index.html", "w", encoding="utf-8") as f:
        f.write(html)

def generate_home(publish_dir):
    """Generate the homepage"""
    env = setup_jinja()
    template = env.get_template('home.html')
    
    # Set is_homepage to True for the homepage
    env.globals['is_homepage'] = True
    
    html = template.render(
        title="vtasca.dev",
        description="Hot takes, ordered chronologically",
        static_prefix="static",
        root_prefix="."
    )
    
    with open(publish_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    
    # Set up directories
    publish_dir, src_dir = set_up_directories()

    # Copy static files
    copy_files(publish_dir, src_dir)

    # Generate blog posts
    with open(src_dir / "blog_metadata.json", "r") as f:
        blog_posts = json.load(f)

    for post in blog_posts:
        convert_markdown_to_html(Path("src/blog/md") / (post['id'] + ".md"), metadata=post, output_dir=publish_dir / "blog")

    # Generate other pages
    generate_home(publish_dir)
    generate_blog_index(blog_posts, publish_dir, src_dir)
