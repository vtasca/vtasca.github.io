from pathlib import Path
import shutil
import json
from markdown2 import Markdown
from jinja2 import Environment, FileSystemLoader
import datetime
import random
import re
import unicodedata
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

    # Tag name -> URL slug, used by templates to link tags to their pages
    env.filters["tag_slug"] = tag_slug

    return env


def tag_slug(tag):
    """Turn a tag name into a URL-safe slug (same rules as fetch.slugify)."""
    value = (
        unicodedata.normalize("NFKD", str(tag)).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def sort_posts(blog_posts):
    """Sort posts newest first by publication (Notion creation) time.

    The metadata has no 'date' key; ISO-8601 timestamps sort correctly as strings.
    """
    return sorted(blog_posts, key=lambda x: x.get("created_time") or "", reverse=True)


def collect_tags(blog_posts):
    """Return [{'name', 'slug', 'count'}] for every tag, most used first, then by name.

    Tags whose names collapse to the same slug are merged under the first name seen.
    """
    tags = {}
    for post in blog_posts:
        for name in dict.fromkeys(post.get("tags", [])):
            slug = tag_slug(name)
            if not slug:
                continue
            entry = tags.setdefault(slug, {"name": name, "slug": slug, "count": 0})
            entry["count"] += 1
    return sorted(tags.values(), key=lambda t: (-t["count"], t["name"].lower()))


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
        created_time=metadata.get("created_time", "") if metadata else "",
        tags=metadata.get("tags", []) if metadata else [],
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

    # Render template
    html = template.render(
        title="Blog",
        description="Controverisal takes, tagged and sorted chronologically",
        posts=sort_posts(blog_posts),
        all_tags=collect_tags(blog_posts),
        active_tag=None,
        static_prefix="../static",
        root_prefix="..",
    )

    # Write the generated index page
    with open(publish_dir / "blog/index.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_tag_pages(blog_posts, publish_dir):
    """Generate blog/tag/<slug>.html for every tag, plus blog/tag/index.html"""
    env = setup_jinja()
    template = env.get_template("blog-index.html")

    tag_dir = publish_dir / "blog" / "tag"
    tag_dir.mkdir(parents=True, exist_ok=True)

    all_tags = collect_tags(blog_posts)
    sorted_posts = sort_posts(blog_posts)

    for tag in all_tags:
        posts = [
            p for p in sorted_posts
            if tag["slug"] in {tag_slug(t) for t in p.get("tags", [])}
        ]
        html = template.render(
            title=f"Posts tagged {tag['name']}",
            description=f"Blog posts tagged {tag['name']}",
            posts=posts,
            all_tags=all_tags,
            active_tag=tag,
            static_prefix="../../static",
            root_prefix="../..",
        )
        with open(tag_dir / f"{tag['slug']}.html", "w", encoding="utf-8") as f:
            f.write(html)

    # Overview of all tags
    tags_template = env.get_template("blog-tags.html")
    html = tags_template.render(
        title="Tags",
        description="All blog tags",
        all_tags=all_tags,
        static_prefix="../../static",
        root_prefix="../..",
    )
    with open(tag_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

    return all_tags


def generate_home(publish_dir):
    """Generate the homepage"""
    env = setup_jinja()
    template = env.get_template("home.html")

    # Set is_homepage to True for the homepage
    env.globals["is_homepage"] = True

    html = template.render(
        title="Home",
        description="A digital garden for experiments, thoughts, data and other such mischief.",
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


def generate_tools(publish_dir):
    """Generate the tools page"""
    env = setup_jinja()
    template = env.get_template("tools.html")

    html = template.render(
        title="Tools",
        description="Useful tools for developers and AI enthusiasts",
        static_prefix="static",
        root_prefix=".",
    )

    with open(publish_dir / "tools.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_data(publish_dir, src_dir):
    """Generate the data page"""
    env = setup_jinja()
    template = env.get_template("data.html")

    # Load dataset metadata
    with open(src_dir / "data_metadata.json", "r") as f:
        datasets = json.load(f)

    html = template.render(
        title="Data Collection",
        description="Curated datasets from various domains, regularly updated and freely available. Each set includes metadata, download options, and mirror links for major platforms.",
        static_prefix="static",
        root_prefix=".",
        datasets=datasets,
    )

    with open(publish_dir / "data.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_tool_pages(publish_dir):
    """Generate individual tool pages"""
    env = setup_jinja()
    
    # Create tools directory
    tools_dir = publish_dir / "tools"
    tools_dir.mkdir(exist_ok=True)
    
    # Generate tokenizer page
    tokenizer_template = env.get_template("tokenizer.html")
    tokenizer_html = tokenizer_template.render(
        title="GPT Tokenizer Tool",
        description="Analyze and tokenize text using OpenAI's GPT models",
        static_prefix="../static",
        root_prefix="..",
    )
    with open(tools_dir / "tokenizer.html", "w", encoding="utf-8") as f:
        f.write(tokenizer_html)
    
    # Generate dithering page
    dithering_template = env.get_template("dithering.html")
    dithering_html = dithering_template.render(
        title="Image Dithering Tool",
        description="Create retro dark aesthetics by applying dithering algorithms to your images",
        static_prefix="../static",
        root_prefix="..",
    )
    with open(tools_dir / "dithering.html", "w", encoding="utf-8") as f:
        f.write(dithering_html)


def generate_logo_page(publish_dir):
    """Generate a blank page with centered logo"""
    env = setup_jinja()
    template = env.get_template("logo.html")

    html = template.render(
        title="Logo",
        description="",
        static_prefix="static",
        root_prefix=".",
    )

    with open(publish_dir / "logo.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_sitemap(publish_dir, src_dir, blog_posts):
    """Generate sitemap.xml"""

    sitemap = """<?xml version='1.0' encoding='utf-8'?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""

    # Get all HTML files recursively from publish_dir
    html_files = []
    for path in publish_dir.rglob("*.html"):
        # Convert to relative path from publish_dir
        rel_path = path.relative_to(publish_dir)
        html_files.append(str(rel_path))

    # Add each URL to sitemap
    for html_file in html_files:
        # Clean up the URL: remove index.html and .html suffixes
        clean_url = html_file
        if clean_url.endswith("index.html"):
            clean_url = clean_url[:-10]  # Remove "index.html"
        elif clean_url.endswith(".html"):
            clean_url = clean_url[:-5]   # Remove ".html"
        
        sitemap += f"\n<url>\n<loc>https://vtasca.dev/{clean_url}</loc>\n</url>"

    sitemap += "\n</urlset>"

    # Write sitemap file
    with open(publish_dir / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)


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
    generate_tag_pages(blog_posts, publish_dir)
    generate_rss_feed(blog_posts, publish_dir)
    generate_contact(publish_dir)
    generate_tools(publish_dir)
    generate_data(publish_dir, src_dir)
    generate_tool_pages(publish_dir)
    generate_logo_page(publish_dir)
    generate_sitemap(publish_dir, src_dir, blog_posts)
