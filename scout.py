import time
import urllib.request
import os
import random
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, 'Config.env')
load_dotenv(ENV_PATH)

blacklist = ["Credit Card Bill", "Gift Card", "Subscription","Volume Control - for Fire TV Stick"]

CATEGORIES = {
    "Baby Products": "https://www.amazon.in/gp/bestsellers/baby/ref=zg_bs_nav_baby_0",
    "Car & Motorbike":"https://www.amazon.in/gp/bestsellers/automotive/ref=zg_bs_nav_automotive_0",
    "Clothing & Accessories":"https://www.amazon.in/gp/bestsellers/apparel/ref=zg_bs_nav_apparel_0",
    "Computers & Accessories":"https://www.amazon.in/gp/bestsellers/computers/ref=zg_bs_nav_computers_0",
    "Home & Kitchen":"https://www.amazon.in/gp/bestsellers/kitchen/ref=zg_bs_nav_kitchen_0",
    "Home Improvement":"https://www.amazon.in/gp/bestsellers/home-improvement/ref=zg_bs_nav_home-improvement_0",
    "Jewellery":"https://www.amazon.in/gp/bestsellers/jewelry/ref=zg_bs_nav_jewelry_0",
    "Musical Instruments":"https://www.amazon.in/gp/bestsellers/musical-instruments/ref=zg_bs_nav_musical-instruments_0",
    "Office Products":"https://www.amazon.in/gp/bestsellers/office/ref=zg_bs_nav_office_0",
    "Shoes & Handbags":"https://www.amazon.in/gp/bestsellers/shoes/ref=zg_bs_nav_shoes_0",
    "Sports, Fitness & Outdoors":"https://www.amazon.in/gp/bestsellers/sports/ref=zg_bs_nav_sports_0",
    "Toys & Games":"https://www.amazon.in/gp/bestsellers/toys/ref=zg_bs_nav_toys_0",
    "Watches":"https://www.amazon.in/gp/bestsellers/watches/ref=zg_bs_nav_watches_0",
    "Collections":"https://www.amazon.in/gp/bestsellers/boost/10894251031/ref=zg_bs_nav_boost_1",
    "HOME":"https://www.amazon.in/gp/bestsellers/boost/10894243031/ref=zg_bs_nav_boost_1",
    "Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1388867031/ref=zg_bs_nav_electronics_1",
    "Cameras & Photography":"https://www.amazon.in/gp/bestsellers/electronics/1388977031/ref=zg_bs_nav_electronics_1",
    "Car & Vehicle Electronics":"https://www.amazon.in/gp/bestsellers/electronics/1389221031/ref=zg_bs_nav_electronics_1",
    "Computers & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1458204031/ref=zg_bs_nav_electronics_1",
    "GPS & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1389315031/ref=zg_bs_nav_electronics_1",
    "Audio Headphones":"https://www.amazon.in/gp/bestsellers/electronics/1388921031/ref=zg_bs_nav_electronics_1",
    "Home Theater, TV & Video":"https://www.amazon.in/gp/bestsellers/electronics/1389375031/ref=zg_bs_nav_electronics_1",
    "Mobiles & Tablets":"https://www.amazon.in/gp/bestsellers/electronics/92071051031/ref=zg_bs_nav_electronics_1",
    "Portable Media Players":"https://www.amazon.in/gp/bestsellers/electronics/1389433031/ref=zg_bs_nav_electronics_1",
    "Radio Communication":"https://www.amazon.in/gp/bestsellers/electronics/1389462031/ref=zg_bs_nav_electronics_1",
    "Telephones & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1389481031/ref=zg_bs_nav_electronics_1",
    "Wearable Technology":"https://www.amazon.in/gp/bestsellers/electronics/11599648031/ref=zg_bs_nav_electronics_1",
    "Home Audio":"https://www.amazon.in/gp/bestsellers/electronics/1389335031/ref=zg_bs_nav_electronics_1"
}

def generate_tags(name, specs):
    base_tags = ["AmazonFinds", "CoolGadgets", "AmazonIndia"]
    keywords = [w for w in name.split() if len(w) > 4][:6]
    return ", ".join(list(set(base_tags + keywords)))

def get_bestsellers(driver, count):
    cat_name, cat_url = random.choice(list(CATEGORIES.items()))
    print(f"🎲 Randomly selected category: {cat_name}")
    
    driver.get(cat_url)
    time.sleep(3)
    products = []
    
    for i in range(count):
        cards = driver.find_elements(By.CSS_SELECTOR, ".zg-grid-general-faceout")
        if i >= len(cards): break
        
        try:
            card = cards[i]

            name = card.text.split('\n')[0].strip()

            if any(keyword in name for keyword in blacklist):
                print(f"⏭️ Skipping: {name}")
                continue

            link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
            asin = link.split("/dp/")[1].split("/")[0]
            
            driver.get(link)
            time.sleep(4)
            
            img_paths = []
            thumbs = driver.find_elements(By.CSS_SELECTOR, "#altImages img")
            found = 0
            for idx, img in enumerate(thumbs):
                if found >= 7: break
                if idx == 1: continue # Skip 2nd image
                
                src = img.get_attribute("src")
                if src and "play-button" not in src:
                    high_res = src.split("._")[0] + ".jpg"
                    local_file = os.path.join(os.getcwd(), f"temp_{i}_{idx}.jpg")
                    urllib.request.urlretrieve(high_res, local_file)
                    img_paths.append(local_file)
                    found += 1
            
            bullets = driver.find_elements(By.CSS_SELECTOR, "#feature-bullets ul li span")
            specs = " | ".join([b.text.strip() for b in bullets if len(b.text.strip()) > 10][:5])
            
            products.append({
                "asin": asin, "name": name, "link": f"{link}?tag=smartcart03b-21",
                "images": img_paths, "specs": specs, "tags": generate_tags(name, specs)
            })
            driver.back()
            time.sleep(3)
        except:
            continue
    return products

def scrape_specific_product(driver, product_url):
    print(f"🎯 Manual Target: {product_url}")
    driver.get(product_url)
    time.sleep(5)

    try:
        name = driver.find_element(By.ID, "productTitle").text.strip()
        asin = product_url.split("/dp/")[1].split("/")[0] if "/dp/" in product_url else "MANUAL"        
        bullets = driver.find_elements(By.CSS_SELECTOR, "#feature-bullets ul li span")
        specs = " | ".join([b.text.strip() for b in bullets if len(b.text.strip()) > 10][:5])
        try:
            price = driver.find_element(By.CSS_SELECTOR, "span.a-price-whole").text
            price = f"₹{price}"
        except:
            price = "Check Link"

        img_paths = []
        thumbs = driver.find_elements(By.CSS_SELECTOR, "#altImages img")
        found = 0
        for idx, img in enumerate(thumbs):
            if found >= 7: break
            src = img.get_attribute("src")
            if not src: continue

            if "play-button" not in src and "._S" in src:
                high_res = src.split("._")[0] + ".jpg"                
                try:
                    local_file = os.path.join(os.getcwd(), f"manual_temp_{found}.jpg")
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                    urllib.request.install_opener(opener)                    
                    urllib.request.urlretrieve(high_res, local_file)                    
                    if os.path.getsize(local_file) > 1000: # Ensure it's a real image
                        img_paths.append(local_file)
                        found += 1
                except Exception as e:
                    print(f"❌ Download failed: {e}")

        return {
            "asin": asin,
            "name": name,
            "link": f"https://www.amazon.in/dp/{asin}?tag={os.getenv("Affiliate_Code")}",
            "price": price,
            "specs": specs,
            "images": img_paths
        }
    except Exception as e:
        print(f"❌ Manual Scrape Failed: {e}")
        return None