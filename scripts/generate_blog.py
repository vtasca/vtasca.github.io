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

NOTION_TOKEN = os.environ['NOTION_TOKEN']
DATABASE_ID = os.environ['DATABASE_ID']

# Initialize the Notion client
notion = Client(auth=os.environ['NOTION_TOKEN'])

def get_database_entries(database_id):
    """
    Fetch all pages from a Notion database
    Returns the full results list containing all page data
    """
    results = []
    
    # Query the database
    response = notion.databases.query(database_id=database_id)
    
    # Add the first set of results
    results.extend(response['results'])
    
    # Continue fetching if there are more results
    while response.get('has_more'):
        response = notion.databases.query(
            database_id=database_id,
            start_cursor=response['next_cursor']
        )
        results.extend(response['results'])
    
    return results

# Get all blog posts
database_id = DATABASE_ID
blog_posts = get_database_entries(database_id)

# ---

def slugify(value, allow_unicode=False):
    """Slugify!"""
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def extract_blog_metadata(posts):
    """
    Extract relevant information from blog posts and format it for JSON export
    """
    blog_data = []
    
    for post in posts:
        properties = post['properties']
        
        # Helper function to safely get text content
        def get_text_content(prop_name, prop_type='rich_text'):
            prop = properties.get(prop_name, {}).get(prop_type, [])
            return prop[0].get('plain_text', '') if prop else ''
        
        # Extract data with safe fallbacks
        metadata = {
            'id': post['id'],
            'name': get_text_content('Name', 'title'),
            'url': slugify(get_text_content('Name', 'title')),
            'description': get_text_content('Description'),
            'tags': [tag['name'] for tag in properties.get('Tags', {}).get('multi_select', [])],
            'published': properties.get('Published Status', {}).get('checkbox', False),
            'created_time': post.get('created_time'),
            'last_edited_time': post.get('last_edited_time')
        }
        
        blog_data.append(metadata)
    
    # Save to JSON file
    with open('blog_posts.json', 'w', encoding='utf-8') as f:
        json.dump(blog_data, f, ensure_ascii=False, indent=2)
    
    return blog_data

# Extract and save blog metadata
blog_metadata = extract_blog_metadata(blog_posts)

# --- Create markdown files

def export_markdown(block_id):
    
    MarkdownExporter(block_id=block_id,
                 output_path="markdown_zip_container",
                 download=True).export()

    try:
        # Find the zip file in the container directory
        zip_path = list(Path('markdown_zip_container').glob('*.zip'))[0]
        
        # Unzip the file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall('temp_extract')

        # Find the markdown file
        markdown_path = list(Path('temp_extract').rglob('*.md'))[0]

        # Move the markdown file to current directory
        shutil.move(str(markdown_path), Path(markdown_path.name))

        # Clean up: remove the container folder and temp directory
        shutil.rmtree('markdown_zip_container')
        shutil.rmtree('temp_extract')
    
    except PermissionError:
        print("Could not access the files. Please ensure they're not open in another program.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
# --- Markdown to html



def convert_markdown_to_html(markdown_file_path):
    """
    Convert a markdown file to HTML using markdown2 and save it to a file.
    
    Args:
        markdown_file_path (str): Path to the markdown file
        
    Returns:
        str: HTML content
    """

    markdowner = Markdown(extras=["fenced-code-blocks", "latex"])


    # Read markdown and convert to HTML
    with open(markdown_file_path) as f:
        html_content = markdowner.convert(f.read())
    
    # Write HTML to file
    html_path = markdown_file_path.replace('.md', '.html')
    with open(html_path, 'w') as f:
        f.write(html_content)
        
    return html_content

corr = "a50d616f-32e1-454f-ad42-8ce0b004a6ee.md"
scraping = "f8d3a26f-1728-4c26-b8ac-964063087412.md"

for item in (corr, scraping):
    convert_markdown_to_html(item)

