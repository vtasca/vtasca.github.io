import re
from collections import defaultdict
import colorsys
import os
from lxml import etree

def hex_to_rgb(hex_color):
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    # Handle both 3 and 6 digit hex
    if len(hex_color) == 3:
        hex_color = ''.join(c + c for c in hex_color)
    
    # Convert to RGB
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_rgb(rgb_str):
    # Extract numbers from rgb(r, g, b) or rgba(r, g, b, a)
    numbers = re.findall(r'\d+', rgb_str)
    return tuple(int(n) for n in numbers[:3])

def is_almost_black(rgb):
    # Consider a color almost black if all components are below 40
    return all(c < 40 for c in rgb)

def get_rgb_from_color(color):
    if color.startswith('#'):
        return hex_to_rgb(color)
    elif color.startswith('rgb'):
        return rgb_to_rgb(color)
    return None

def is_dark_element(element):
    # Check direct color attributes
    for attr in ['fill', 'stroke', 'color']:
        if attr in element.attrib:
            color = element.attrib[attr]
            if color != 'none' and color != 'transparent':
                rgb = get_rgb_from_color(color)
                if rgb and is_almost_black(rgb):
                    return True
    
    # Check style attribute
    if 'style' in element.attrib:
        style = element.attrib['style']
        color_pattern = re.compile(r'(?:fill|stroke|color):\s*(#[0-9a-fA-F]{3,6}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)|rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\))')
        matches = color_pattern.findall(style)
        for color in matches:
            rgb = get_rgb_from_color(color)
            if rgb and is_almost_black(rgb):
                return True
    
    return False

def process_svg(svg_file, fill_color):
    # Parse the SVG file with lxml
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(svg_file, parser)
    root = tree.getroot()
    
    # Regular expression to find colors in style attributes
    color_pattern = re.compile(r'(?:fill|stroke|color):\s*(#[0-9a-fA-F]{3,6}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)|rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\))')
    
    def process_element(element):
        # Process children first (in reverse order to avoid index issues when removing)
        for child in reversed(list(element)):
            if process_element(child):
                element.remove(child)
        
        # If element is not dark, update its colors
        if not is_dark_element(element):
            # Update direct color attributes
            for attr in ['fill', 'stroke', 'color']:
                if attr in element.attrib:
                    color = element.attrib[attr]
                    if color != 'none' and color != 'transparent':
                        element.attrib[attr] = fill_color
            
            # Update style attribute
            if 'style' in element.attrib:
                style = element.attrib['style']
                new_style = style
                
                # Find all color declarations in style
                for match in color_pattern.finditer(style):
                    color = match.group(1)
                    rgb = get_rgb_from_color(color)
                    if rgb and not is_almost_black(rgb):
                        new_style = new_style.replace(color, fill_color)
                
                element.attrib['style'] = new_style
        
        return is_dark_element(element)
    
    # Process all elements
    process_element(root)
    
    # Save the modified SVG back to the original file
    tree.write(svg_file, pretty_print=True, xml_declaration=True, encoding='utf-8')
    return svg_file

def analyze_svg_colors(svg_file):
    # Parse the SVG file with lxml
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(svg_file, parser)
    root = tree.getroot()
    
    # Dictionaries to store unique colors
    dark_colors = defaultdict(int)
    other_colors = defaultdict(int)
    
    # Regular expression to find colors in style attributes
    color_pattern = re.compile(r'(?:fill|stroke|color):\s*(#[0-9a-fA-F]{3,6}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)|rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\))')
    
    def process_element(element):
        # Check direct color attributes
        for attr in ['fill', 'stroke', 'color']:
            if attr in element.attrib:
                color = element.attrib[attr]
                if color != 'none' and color != 'transparent':
                    rgb = get_rgb_from_color(color)
                    if rgb:
                        if is_almost_black(rgb):
                            dark_colors[color] += 1
                        else:
                            other_colors[color] += 1
        
        # Check style attribute
        if 'style' in element.attrib:
            style = element.attrib['style']
            matches = color_pattern.findall(style)
            for color in matches:
                rgb = get_rgb_from_color(color)
                if rgb:
                    if is_almost_black(rgb):
                        dark_colors[color] += 1
                    else:
                        other_colors[color] += 1
        
        # Recursively process child elements
        for child in element:
            process_element(child)
    
    # Process all elements
    process_element(root)
    
    return dark_colors, other_colors

def main():
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python process_svg.py <svg_file> <fill_color_hex>")
        print("Example: python process_svg.py icon.svg FF0000")
        sys.exit(1)
    
    svg_file = sys.argv[1]
    fill_color = sys.argv[2]
    
    # Validate hex color
    hex_pattern = re.compile(r'^#?[0-9a-fA-F]{3,6}$')
    if not hex_pattern.match(fill_color):
        print("Error: Fill color must be a valid hex color (e.g., FF0000)")
        sys.exit(1)
    
    # Ensure hex color has # prefix
    if not fill_color.startswith('#'):
        fill_color = '#' + fill_color
    
    try:
        # First, show the color analysis
        dark_colors, other_colors = analyze_svg_colors(svg_file)
        
        print("\nDark Colors (will be removed):")
        print("-" * 40)
        for color, count in sorted(dark_colors.items()):
            print(f"{color} (used {count} times)")
            
        print("\nOther Colors (will be changed to {fill_color}):")
        print("-" * 40)
        for color, count in sorted(other_colors.items()):
            print(f"{color} (used {count} times)")
        
        # Process the SVG
        output_file = process_svg(svg_file, fill_color)
        print(f"\nSVG file has been updated in place: {output_file}")
        print("Dark elements have been removed, and remaining elements have been colored with {fill_color}")
            
    except Exception as e:
        print(f"Error processing SVG file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 