"""
Royal Road Story Scraper
Downloads free chapters from Royal Road for personal reference.
Uses cloudscraper to bypass Cloudflare protection.
Respects rate limits (2s delay between requests).

Usage:
    python rr_scraper.py                    # scrape all configured stories
    python rr_scraper.py --story 21410      # scrape specific story by ID
    python rr_scraper.py --max-chapters 5   # limit chapters per story
"""
import argparse, os, re, sys, time
import cloudscraper
from bs4 import BeautifulSoup

# ============================================================
# Configuration
# ============================================================
OUTPUT_DIR = r"H:\Python学习\AI写小说\royalroad_archive"

STORIES = {
    # id: (name, slug)
    166539: ("Blind Boxes Open Up Miniature Worlds", "blind-boxes-open-up-miniature-worlds-kingdom-building"),
    76469: ("Inexorable Chaos", "inexorable-chaos-god-games"),
}

DELAY = 2.0  # seconds between requests


def get_soup(scraper, url):
    """Fetch URL and return BeautifulSoup object."""
    r = scraper.get(url)
    r.raise_for_status()
    return BeautifulSoup(r.text, 'html.parser')


def get_chapter_list(scraper, story_id, story_slug, max_chapters=None):
    """Extract unique chapter URLs from story main page."""
    base_url = f"https://www.royalroad.com/fiction/{story_id}/{story_slug}"
    soup = get_soup(scraper, base_url)

    # Find chapter rows in the table
    seen_urls = set()
    chapters = []
    
    for row in soup.select('#chapters tbody tr'):
        link = row.select_one('a[href*="/chapter/"]')
        if not link:
            continue
        url = link['href']
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        # Extract metadata
        full_url = f"https://www.royalroad.com{url}"
        title = link.get_text(strip=True)
        
        # Get date from row
        time_el = row.select_one('time')
        date = time_el.get_text(strip=True) if time_el else ''
        
        chapters.append({
            'url': full_url,
            'title': title,
            'date': date,
        })
    
    print(f"  Found {len(chapters)} unique chapters")
    
    if max_chapters and len(chapters) > max_chapters:
        chapters = chapters[:max_chapters]
        print(f"  Limited to {max_chapters} chapters")
    
    return chapters


def fetch_chapter(scraper, chapter_url):
    """Fetch a single chapter and extract text."""
    soup = get_soup(scraper, chapter_url)
    content = soup.select_one('.chapter-content')
    if not content:
        return None, "Chapter content not found"
    
    # Remove script/style tags
    for tag in content(['script', 'style']):
        tag.decompose()
    
    text = content.get_text(separator='\n', strip=True)
    return text, None


def safe_filename(s):
    """Convert string to safe filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', s).strip()


def scrape_story(scraper, story_id, story_name, story_slug, max_chapters=None):
    """Scrape all chapters of a story."""
    print(f"\n{'='*60}")
    print(f"📖 {story_name} (ID: {story_id})")
    print(f"{'='*60}")
    
    story_dir = os.path.join(OUTPUT_DIR, safe_filename(story_name))
    os.makedirs(story_dir, exist_ok=True)
    
    # Get chapter list
    chapters = get_chapter_list(scraper, story_id, story_slug, max_chapters)
    if not chapters:
        print("  ⚠️ No chapters found")
        return
    
    success = 0
    failed = 0
    
    for i, ch in enumerate(chapters, 1):
        print(f"  [{i}/{len(chapters)}] {ch['title'][:60]}...", end=' ', flush=True)
        
        text, err = fetch_chapter(scraper, ch['url'])
        
        if err:
            print(f"❌ {err}")
            failed += 1
            continue
        
        # Save to file
        filename = f"{i:03d}_{safe_filename(ch['title'])}.txt"
        filepath = os.path.join(story_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Title: {ch['title']}\n")
            f.write(f"Source: {ch['url']}\n")
            f.write(f"Date: {ch['date']}\n")
            f.write(f"Words: {len(text.split())}\n")
            f.write("=" * 60 + "\n\n")
            f.write(text)
        
        print(f"✅ {len(text.split())} words")
        success += 1
        
        time.sleep(DELAY)
    
    print(f"\n  Done: {success} OK, {failed} FAIL")


def main():
    parser = argparse.ArgumentParser(description='Royal Road Story Scraper')
    parser.add_argument('--story', type=int, help='Specific story ID to scrape')
    parser.add_argument('--max-chapters', type=int, default=0, 
                        help='Max chapters per story (0=all)')
    args = parser.parse_args()
    
    print("🚀 Royal Road Scraper")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Delay: {DELAY}s between requests")
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    if args.story:
        if args.story not in STORIES:
            print(f"❌ Unknown story ID: {args.story}")
            print(f"   Known IDs: {list(STORIES.keys())}")
            sys.exit(1)
        name, slug = STORIES[args.story]
        max_ch = args.max_chapters if args.max_chapters > 0 else None
        scrape_story(scraper, args.story, name, slug, max_ch)
    else:
        max_ch = args.max_chapters if args.max_chapters > 0 else None
        for sid, (sname, sslug) in STORIES.items():
            scrape_story(scraper, sid, sname, sslug, max_ch)
    
    print(f"\n✨ All done! Files saved to: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
