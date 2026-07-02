import time
import urllib.request
import os
import random
import json
import re
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, 'Config.env')
load_dotenv(ENV_PATH)

blacklist = ["Credit Card", "Gift Card", "Subscription", "recharge", "lpg", "amazon pay", "blink plus"]

CATEGORIES = {
    "Bestsellers/Amazon Launchpad":"https://www.amazon.in/gp/bestsellers/boost/ref=zg_bs_nav_boost_0",
    "Bestsellers/Amazon Renewed":"https://www.amazon.in/gp/bestsellers/amazon-renewed/ref=zg_bs_nav_amazon-renewed_0",
    "Bestsellers/Apps & Games":"https://www.amazon.in/gp/bestsellers/mobile-apps/ref=zg_bs_nav_mobile-apps_0",
    "Bestsellers/Baby Products":"https://www.amazon.in/gp/bestsellers/baby/ref=zg_bs_nav_baby_0",
    "Bestsellers/Bags, Wallets and Luggage":"https://www.amazon.in/gp/bestsellers/luggage/ref=zg_bs_nav_luggage_0",
    "Bestsellers/Beauty":"https://www.amazon.in/gp/bestsellers/beauty/ref=zg_bs_nav_beauty_0",
    "Bestsellers/Books":"https://www.amazon.in/gp/bestsellers/books/ref=zg_bs_nav_books_0",
    "Bestsellers/Car & Motorbike":"https://www.amazon.in/gp/bestsellers/automotive/ref=zg_bs_nav_automotive_0",
    "Bestsellers/Clothing & Accessories":"https://www.amazon.in/gp/bestsellers/apparel/ref=zg_bs_nav_apparel_0",
    "Bestsellers/Computers & Accessories":"https://www.amazon.in/gp/bestsellers/computers/ref=zg_bs_nav_computers_0",
    "Bestsellers/Electronics":"https://www.amazon.in/gp/bestsellers/electronics/ref=zg_bs_nav_electronics_0",
    "Bestsellers/Garden & Outdoors":"https://www.amazon.in/gp/bestsellers/garden/ref=zg_bs_nav_garden_0",
    "Bestsellers/Gift Cards":"https://www.amazon.in/gp/bestsellers/gift-cards/ref=zg_bs_nav_gift-cards_0",
    "Bestsellers/Grocery & Gourmet Foods":"https://www.amazon.in/gp/bestsellers/grocery/ref=zg_bs_nav_grocery_0",
    "Bestsellers/Health & Personal Care":"https://www.amazon.in/gp/bestsellers/hpc/ref=zg_bs_nav_hpc_0",
    "Bestsellers/Home & Kitchen":"https://www.amazon.in/gp/bestsellers/kitchen/ref=zg_bs_nav_kitchen_0",
    "Bestsellers/Home Improvement":"https://www.amazon.in/gp/bestsellers/home-improvement/ref=zg_bs_nav_home-improvement_0",
    "Bestsellers/Industrial & Scientific":"https://www.amazon.in/gp/bestsellers/industrial/ref=zg_bs_nav_industrial_0",
    "Bestsellers/Jewellery":"https://www.amazon.in/gp/bestsellers/jewelry/ref=zg_bs_nav_jewelry_0",
    "Bestsellers/Kindle Store":"https://www.amazon.in/gp/bestsellers/digital-text/ref=zg_bs_nav_digital-text_0",
    "Bestsellers/Movies & TV Shows":"https://www.amazon.in/gp/bestsellers/dvd/ref=zg_bs_nav_dvd_0",
    "Bestsellers/Music":"https://www.amazon.in/gp/bestsellers/music/ref=zg_bs_nav_music_0",
    "Bestsellers/Musical Instruments":"https://www.amazon.in/gp/bestsellers/musical-instruments/ref=zg_bs_nav_musical-instruments_0",
    "Bestsellers/Office Products":"https://www.amazon.in/gp/bestsellers/office/ref=zg_bs_nav_office_0",
    "Bestsellers/Pet Supplies":"https://www.amazon.in/gp/bestsellers/pet-supplies/ref=zg_bs_nav_pet-supplies_0",
    "Bestsellers/Shoes & Handbags":"https://www.amazon.in/gp/bestsellers/shoes/ref=zg_bs_nav_shoes_0",
    "Bestsellers/Software":"https://www.amazon.in/gp/bestsellers/software/ref=zg_bs_nav_software_0",
    "Bestsellers/Sports, Fitness & Outdoors":"https://www.amazon.in/gp/bestsellers/sports/ref=zg_bs_nav_sports_0",
    "Bestsellers/Toys & Games":"https://www.amazon.in/gp/bestsellers/toys/ref=zg_bs_nav_toys_0",
    "Bestsellers/Video Games":"https://www.amazon.in/gp/bestsellers/videogames/ref=zg_bs_nav_videogames_0",
    "Bestsellers/Watches":"https://www.amazon.in/gp/bestsellers/watches/ref=zg_bs_nav_watches_0",
    "Amazon Launchpad/Body":"https://www.amazon.in/gp/bestsellers/boost/10894224031/ref=zg_bs_nav_boost_1",
    "Amazon Launchpad/Collections":"https://www.amazon.in/gp/bestsellers/boost/10894251031/ref=zg_bs_nav_boost_1",
    "Amazon Launchpad/Electronics":"https://www.amazon.in/gp/bestsellers/boost/10894234031/ref=zg_bs_nav_boost_1",
    "Amazon Launchpad/Fashion Accessories":"https://www.amazon.in/gp/bestsellers/boost/17161295031/ref=zg_bs_nav_boost_1",
    "Amazon Launchpad/Food":"https://www.amazon.in/gp/bestsellers/boost/10894230031/ref=zg_bs_nav_boost_1",
    "Amazon Launchpad/Home":"https://www.amazon.in/gp/bestsellers/boost/10894243031/ref=zg_bs_nav_boost_1",
    "Amazon Launchpad/Toys & Baby":"https://www.amazon.in/gp/bestsellers/boost/14091152031/ref=zg_bs_nav_boost_1",
    "Amazon Renewed/Amazon Launchpad":"https://www.amazon.in/gp/bestsellers/boost/ref=zg_bs_nav_boost_0_amazon-renewed",
    "Amazon Renewed/Apps & Games":"https://www.amazon.in/gp/bestsellers/mobile-apps/ref=zg_bs_nav_mobile-apps_0_amazon-renewed",
    "Amazon Renewed/Baby Products":"https://www.amazon.in/gp/bestsellers/baby/ref=zg_bs_nav_baby_0_amazon-renewed",
    "Amazon Renewed/Bags, Wallets and Luggage":"https://www.amazon.in/gp/bestsellers/luggage/ref=zg_bs_nav_luggage_0_amazon-renewed",
    "Amazon Renewed/Beauty":"https://www.amazon.in/gp/bestsellers/beauty/ref=zg_bs_nav_beauty_0_amazon-renewed",
    "Amazon Renewed/Books":"https://www.amazon.in/gp/bestsellers/books/ref=zg_bs_nav_books_0_amazon-renewed",
    "Amazon Renewed/Car & Motorbike":"https://www.amazon.in/gp/bestsellers/automotive/ref=zg_bs_nav_automotive_0_amazon-renewed",
    "Amazon Renewed/Clothing & Accessories":"https://www.amazon.in/gp/bestsellers/apparel/ref=zg_bs_nav_apparel_0_amazon-renewed",
    "Amazon Renewed/Computers & Accessories":"https://www.amazon.in/gp/bestsellers/computers/ref=zg_bs_nav_computers_0_amazon-renewed",
    "Amazon Renewed/Electronics":"https://www.amazon.in/gp/bestsellers/electronics/ref=zg_bs_nav_electronics_0_amazon-renewed",
    "Amazon Renewed/Garden & Outdoors":"https://www.amazon.in/gp/bestsellers/garden/ref=zg_bs_nav_garden_0_amazon-renewed",
    "Amazon Renewed/Gift Cards":"https://www.amazon.in/gp/bestsellers/gift-cards/ref=zg_bs_nav_gift-cards_0_amazon-renewed",
    "Amazon Renewed/Grocery & Gourmet Foods":"https://www.amazon.in/gp/bestsellers/grocery/ref=zg_bs_nav_grocery_0_amazon-renewed",
    "Amazon Renewed/Health & Personal Care":"https://www.amazon.in/gp/bestsellers/hpc/ref=zg_bs_nav_hpc_0_amazon-renewed",
    "Amazon Renewed/Home & Kitchen":"https://www.amazon.in/gp/bestsellers/kitchen/ref=zg_bs_nav_kitchen_0_amazon-renewed",
    "Amazon Renewed/Home Improvement":"https://www.amazon.in/gp/bestsellers/home-improvement/ref=zg_bs_nav_home-improvement_0_amazon-renewed",
    "Amazon Renewed/Industrial & Scientific":"https://www.amazon.in/gp/bestsellers/industrial/ref=zg_bs_nav_industrial_0_amazon-renewed",
    "Amazon Renewed/Jewellery":"https://www.amazon.in/gp/bestsellers/jewelry/ref=zg_bs_nav_jewelry_0_amazon-renewed",
    "Amazon Renewed/Kindle Store":"https://www.amazon.in/gp/bestsellers/digital-text/ref=zg_bs_nav_digital-text_0_amazon-renewed",
    "Amazon Renewed/Movies & TV Shows":"https://www.amazon.in/gp/bestsellers/dvd/ref=zg_bs_nav_dvd_0_amazon-renewed",
    "Amazon Renewed/Music":"https://www.amazon.in/gp/bestsellers/music/ref=zg_bs_nav_music_0_amazon-renewed",
    "Amazon Renewed/Musical Instruments":"https://www.amazon.in/gp/bestsellers/musical-instruments/ref=zg_bs_nav_musical-instruments_0_amazon-renewed",
    "Amazon Renewed/Office Products":"https://www.amazon.in/gp/bestsellers/office/ref=zg_bs_nav_office_0_amazon-renewed",
    "Amazon Renewed/Pet Supplies":"https://www.amazon.in/gp/bestsellers/pet-supplies/ref=zg_bs_nav_pet-supplies_0_amazon-renewed",
    "Amazon Renewed/Shoes & Handbags":"https://www.amazon.in/gp/bestsellers/shoes/ref=zg_bs_nav_shoes_0_amazon-renewed",
    "Amazon Renewed/Software":"https://www.amazon.in/gp/bestsellers/software/ref=zg_bs_nav_software_0_amazon-renewed",
    "Amazon Renewed/Sports, Fitness & Outdoors":"https://www.amazon.in/gp/bestsellers/sports/ref=zg_bs_nav_sports_0_amazon-renewed",
    "Amazon Renewed/Toys & Games":"https://www.amazon.in/gp/bestsellers/toys/ref=zg_bs_nav_toys_0_amazon-renewed",
    "Amazon Renewed/Video Games":"https://www.amazon.in/gp/bestsellers/videogames/ref=zg_bs_nav_videogames_0_amazon-renewed",
    "Amazon Renewed/Watches":"https://www.amazon.in/gp/bestsellers/watches/ref=zg_bs_nav_watches_0_amazon-renewed",
    "Apps & Games/Books & Comics":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385384031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Business":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385388031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Communication":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385396031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Customization":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385397031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Education":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385404031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Finance":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385405031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Food & Drink":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385416031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Games":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385421031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Health & Fitness":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385470031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Kids":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385481031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Lifestyle":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385601031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Local":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385632031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Magazines":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385640031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Medical":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385680031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Movies & TV":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385685031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Music & Audio":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385691031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/News":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385705031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Novelty":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385712031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Photo & Video":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385735031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Productivity":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385736031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Reference":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385744031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Shopping":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385760031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Social":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385761031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Sports":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385773031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Transportation":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385808031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Travel":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385813031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Utilities":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385820031/ref=zg_bs_nav_mobile-apps_1",
    "Apps & Games/Weather":"https://www.amazon.in/gp/bestsellers/mobile-apps/9385853031/ref=zg_bs_nav_mobile-apps_1",
    "Baby Products/Activity & Entertainment":"https://www.amazon.in/gp/bestsellers/baby/1953106031/ref=zg_bs_nav_baby_1",
    "Baby Products/Baby & Toddler Toys":"https://www.amazon.in/gp/bestsellers/baby/1378175031/ref=zg_bs_nav_baby_1",
    "Baby Products/Baby Care":"https://www.amazon.in/gp/bestsellers/baby/1953111031/ref=zg_bs_nav_baby_1",
    "Baby Products/Baby Carriers":"https://www.amazon.in/gp/bestsellers/baby/1953143031/ref=zg_bs_nav_baby_1",
    "Baby Products/Baby Shoes":"https://www.amazon.in/gp/bestsellers/baby/1953272031/ref=zg_bs_nav_baby_1",
    "Baby Products/Car Seats & Accessories":"https://www.amazon.in/gp/bestsellers/baby/1953279031/ref=zg_bs_nav_baby_1",
    "Baby Products/Maternity":"https://www.amazon.in/gp/bestsellers/baby/1953294031/ref=zg_bs_nav_baby_1",
    "Baby Products/Nappy Changing":"https://www.amazon.in/gp/bestsellers/baby/1953345031/ref=zg_bs_nav_baby_1",
    "Baby Products/Nursery":"https://www.amazon.in/gp/bestsellers/baby/1953359031/ref=zg_bs_nav_baby_1",
    "Baby Products/Nursing & Feeding":"https://www.amazon.in/gp/bestsellers/baby/1953448031/ref=zg_bs_nav_baby_1",
    "Baby Products/Potty Training & Step Stools":"https://www.amazon.in/gp/bestsellers/baby/1953474031/ref=zg_bs_nav_baby_1",
    "Baby Products/Safety Equipment":"https://www.amazon.in/gp/bestsellers/baby/1953501031/ref=zg_bs_nav_baby_1",
    "Baby Products/Soothers & Teethers":"https://www.amazon.in/gp/bestsellers/baby/1953514031/ref=zg_bs_nav_baby_1",
    "Baby Products/Strollers & Prams":"https://www.amazon.in/gp/bestsellers/baby/1953480031/ref=zg_bs_nav_baby_1",
    "Baby Products/Trailers":"https://www.amazon.in/gp/bestsellers/baby/1953519031/ref=zg_bs_nav_baby_1",
    "Bags, Wallets and Luggage/Backpacks":"https://www.amazon.in/gp/bestsellers/luggage/2917430031/ref=zg_bs_nav_luggage_1",
    "Bags, Wallets and Luggage/Bags & Briefcases":"https://www.amazon.in/gp/bestsellers/luggage/2917431031/ref=zg_bs_nav_luggage_1",
    "Bags, Wallets and Luggage/Luggage":"https://www.amazon.in/gp/bestsellers/luggage/2917432031/ref=zg_bs_nav_luggage_1",
    "Bags, Wallets and Luggage/Shopping Bags & Baskets":"https://www.amazon.in/gp/bestsellers/luggage/2917433031/ref=zg_bs_nav_luggage_1",
    "Bags, Wallets and Luggage/Travel Accessories":"https://www.amazon.in/gp/bestsellers/luggage/2917434031/ref=zg_bs_nav_luggage_1",
    "Bags, Wallets and Luggage/Wallets, Card Cases & Money Organizers":"https://www.amazon.in/gp/bestsellers/luggage/2917484031/ref=zg_bs_nav_luggage_1",
    "Beauty/Bath & Shower":"https://www.amazon.in/gp/bestsellers/beauty/1374276031/ref=zg_bs_nav_beauty_1",
    "Beauty/Fragrance":"https://www.amazon.in/gp/bestsellers/beauty/1374298031/ref=zg_bs_nav_beauty_1",
    "Beauty/Hair Care":"https://www.amazon.in/gp/bestsellers/beauty/9851597031/ref=zg_bs_nav_beauty_1",
    "Beauty/Make-up":"https://www.amazon.in/gp/bestsellers/beauty/1374357031/ref=zg_bs_nav_beauty_1",
    "Beauty/Manicure & Pedicure":"https://www.amazon.in/gp/bestsellers/beauty/27983606031/ref=zg_bs_nav_beauty_1",
    "Beauty/Skin Care":"https://www.amazon.in/gp/bestsellers/beauty/1374407031/ref=zg_bs_nav_beauty_1",
    "Beauty/Tools & Accessories":"https://www.amazon.in/gp/bestsellers/beauty/1374450031/ref=zg_bs_nav_beauty_1",
    "Books/Action & Adventure":"https://www.amazon.in/gp/bestsellers/books/1318158031/ref=zg_bs_nav_books_1",
    "Books/Arts, Film & Photography":"https://www.amazon.in/gp/bestsellers/books/1318052031/ref=zg_bs_nav_books_1",
    "Books/Biographies, Diaries & True Accounts":"https://www.amazon.in/gp/bestsellers/books/1318064031/ref=zg_bs_nav_books_1",
    "Books/Business & Economics":"https://www.amazon.in/gp/bestsellers/books/1318068031/ref=zg_bs_nav_books_1",
    "Books/Children's Books":"https://www.amazon.in/gp/bestsellers/books/64619755031/ref=zg_bs_nav_books_1",
    "Books/Comics & Mangas":"https://www.amazon.in/gp/bestsellers/books/1318104031/ref=zg_bs_nav_books_1",
    "Books/Computing, Internet & Digital Media":"https://www.amazon.in/gp/bestsellers/books/1318105031/ref=zg_bs_nav_books_1",
    "Books/Crafts, Home & Lifestyle":"https://www.amazon.in/gp/bestsellers/books/1318118031/ref=zg_bs_nav_books_1",
    "Books/Crime, Thriller & Mystery":"https://www.amazon.in/gp/bestsellers/books/1318161031/ref=zg_bs_nav_books_1",
    "Books/Engineering":"https://www.amazon.in/gp/bestsellers/books/22960344031/ref=zg_bs_nav_books_1",
    "Books/Exam Preparation":"https://www.amazon.in/gp/bestsellers/books/4149751031/ref=zg_bs_nav_books_1",
    "Books/Fantasy, Horror & Science Fiction":"https://www.amazon.in/gp/bestsellers/books/1402038031/ref=zg_bs_nav_books_1",
    "Books/Health, Family & Personal Development":"https://www.amazon.in/gp/bestsellers/books/1318128031/ref=zg_bs_nav_books_1",
    "Books/Health, Fitness & Nutrition":"https://www.amazon.in/gp/bestsellers/books/23033693031/ref=zg_bs_nav_books_1",
    "Books/Higher Education Textbooks":"https://www.amazon.in/gp/bestsellers/books/4149418031/ref=zg_bs_nav_books_1",
    "Books/Historical Fiction":"https://www.amazon.in/gp/bestsellers/books/1318164031/ref=zg_bs_nav_books_1",
    "Books/History":"https://www.amazon.in/gp/bestsellers/books/4149493031/ref=zg_bs_nav_books_1",
    "Books/Humour":"https://www.amazon.in/gp/bestsellers/books/1318143031/ref=zg_bs_nav_books_1",
    "Books/Language, Linguistics & Writing":"https://www.amazon.in/gp/bestsellers/books/1318144031/ref=zg_bs_nav_books_1",
    "Books/Law":"https://www.amazon.in/gp/bestsellers/books/4149542031/ref=zg_bs_nav_books_1",
    "Books/Literature & Fiction":"https://www.amazon.in/gp/bestsellers/books/1318157031/ref=zg_bs_nav_books_1",
    "Books/Maps & Atlases":"https://www.amazon.in/gp/bestsellers/books/1318298031/ref=zg_bs_nav_books_1",
    "Books/Medicine & Health Sciences":"https://www.amazon.in/gp/bestsellers/books/4149549031/ref=zg_bs_nav_books_1",
    "Books/Politics":"https://www.amazon.in/gp/bestsellers/books/1318176031/ref=zg_bs_nav_books_1",
    "Books/Reference":"https://www.amazon.in/gp/bestsellers/books/1318185031/ref=zg_bs_nav_books_1",
    "Books/Religion":"https://www.amazon.in/gp/bestsellers/books/1318188031/ref=zg_bs_nav_books_1",
    "Books/Romance":"https://www.amazon.in/gp/bestsellers/books/1318168031/ref=zg_bs_nav_books_1",
    "Books/School Books":"https://www.amazon.in/gp/bestsellers/books/4149807031/ref=zg_bs_nav_books_1",
    "Books/Science & Mathematics":"https://www.amazon.in/gp/bestsellers/books/4149708031/ref=zg_bs_nav_books_1",
    "Books/Sciences, Technology & Medicine":"https://www.amazon.in/gp/bestsellers/books/1318203031/ref=zg_bs_nav_books_1",
    "Books/Society & Social Sciences":"https://www.amazon.in/gp/bestsellers/books/1318216031/ref=zg_bs_nav_books_1",
    "Books/Sports":"https://www.amazon.in/gp/bestsellers/books/1318224031/ref=zg_bs_nav_books_1",
    "Books/Teen & Young Adult":"https://www.amazon.in/gp/bestsellers/books/64619754031/ref=zg_bs_nav_books_1",
    "Books/Textbooks & Study Guides":"https://www.amazon.in/gp/bestsellers/books/15417300031/ref=zg_bs_nav_books_1",
    "Books/Travel":"https://www.amazon.in/gp/bestsellers/books/1318295031/ref=zg_bs_nav_books_1",
    "Car & Motorbike/Car & Motorbike Care":"https://www.amazon.in/gp/bestsellers/automotive/5257472031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Car & Vehicle Electronics":"https://www.amazon.in/gp/bestsellers/automotive/5257473031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Car Accessories":"https://www.amazon.in/gp/bestsellers/automotive/5257474031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Car Parts":"https://www.amazon.in/gp/bestsellers/automotive/5257475031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Car Tyres & Rims":"https://www.amazon.in/gp/bestsellers/automotive/5257476031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Gifts & Merchandise":"https://www.amazon.in/gp/bestsellers/automotive/5257477031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Motorbikes, Accessories & Parts":"https://www.amazon.in/gp/bestsellers/automotive/5257478031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Motorhome Parts & Accessories":"https://www.amazon.in/gp/bestsellers/automotive/5257479031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Navigation Devices":"https://www.amazon.in/gp/bestsellers/automotive/5257480031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Oils & Fluids":"https://www.amazon.in/gp/bestsellers/automotive/5257481031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Paintwork":"https://www.amazon.in/gp/bestsellers/automotive/5257482031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Tools & Equipment":"https://www.amazon.in/gp/bestsellers/automotive/5257483031/ref=zg_bs_nav_automotive_1",
    "Car & Motorbike/Transporting & Storage":"https://www.amazon.in/gp/bestsellers/automotive/5257484031/ref=zg_bs_nav_automotive_1",
    "Clothing & Accessories/Baby":"https://www.amazon.in/gp/bestsellers/apparel/1953148031/ref=zg_bs_nav_apparel_1",
    "Clothing & Accessories/Boys":"https://www.amazon.in/gp/bestsellers/apparel/1967851031/ref=zg_bs_nav_apparel_1",
    "Clothing & Accessories/Girls":"https://www.amazon.in/gp/bestsellers/apparel/1967936031/ref=zg_bs_nav_apparel_1",
    "Clothing & Accessories/Men":"https://www.amazon.in/gp/bestsellers/apparel/1968024031/ref=zg_bs_nav_apparel_1",
    "Clothing & Accessories/Sport Specific Clothing":"https://www.amazon.in/gp/bestsellers/apparel/26978634031/ref=zg_bs_nav_apparel_1",
    "Clothing & Accessories/Women":"https://www.amazon.in/gp/bestsellers/apparel/1953602031/ref=zg_bs_nav_apparel_1",
    "Computers & Accessories/Accessories":"https://www.amazon.in/gp/bestsellers/computers/1375248031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Audio & Video Accessories":"https://www.amazon.in/gp/bestsellers/computers/1375459031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Components":"https://www.amazon.in/gp/bestsellers/computers/1375344031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Desktops":"https://www.amazon.in/gp/bestsellers/computers/1375392031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/External Devices & Data Storage":"https://www.amazon.in/gp/bestsellers/computers/1375393031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Keyboards, Mice & Input Devices":"https://www.amazon.in/gp/bestsellers/computers/1375412031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Laptops":"https://www.amazon.in/gp/bestsellers/computers/1375424031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Monitors":"https://www.amazon.in/gp/bestsellers/computers/1375425031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Networking Devices":"https://www.amazon.in/gp/bestsellers/computers/1375427031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/PC Speakers":"https://www.amazon.in/gp/bestsellers/computers/1375442031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Printers, Inks & Accessories":"https://www.amazon.in/gp/bestsellers/computers/14784019031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Scanners":"https://www.amazon.in/gp/bestsellers/computers/1375452031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Servers":"https://www.amazon.in/gp/bestsellers/computers/1375457031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Streaming Clients":"https://www.amazon.in/gp/bestsellers/computers/1389342031/ref=zg_bs_nav_computers_1",
    "Computers & Accessories/Tablets":"https://www.amazon.in/gp/bestsellers/computers/1375458031/ref=zg_bs_nav_computers_1",
    "Electronics/Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1388867031/ref=zg_bs_nav_electronics_1",
    "Electronics/Cameras & Photography":"https://www.amazon.in/gp/bestsellers/electronics/1388977031/ref=zg_bs_nav_electronics_1",
    "Electronics/Car & Vehicle Electronics":"https://www.amazon.in/gp/bestsellers/electronics/1389221031/ref=zg_bs_nav_electronics_1",
    "Electronics/Computers & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1458204031/ref=zg_bs_nav_electronics_1",
    "Electronics/GPS & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1389315031/ref=zg_bs_nav_electronics_1",
    "Electronics/Headphones":"https://www.amazon.in/gp/bestsellers/electronics/1388921031/ref=zg_bs_nav_electronics_1",
    "Electronics/Hi-Fi & Home Audio":"https://www.amazon.in/gp/bestsellers/electronics/1389335031/ref=zg_bs_nav_electronics_1",
    "Electronics/Home Theatre, TV & Video":"https://www.amazon.in/gp/bestsellers/electronics/1389375031/ref=zg_bs_nav_electronics_1",
    "Electronics/Mobiles & Tablets":"https://www.amazon.in/gp/bestsellers/electronics/92071051031/ref=zg_bs_nav_electronics_1",
    "Electronics/Portable Media Players":"https://www.amazon.in/gp/bestsellers/electronics/1389433031/ref=zg_bs_nav_electronics_1",
    "Electronics/Radio Communication":"https://www.amazon.in/gp/bestsellers/electronics/1389462031/ref=zg_bs_nav_electronics_1",
    "Electronics/Telephones & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1389481031/ref=zg_bs_nav_electronics_1",
    "Electronics/Warranties":"https://www.amazon.in/gp/bestsellers/electronics/1389493031/ref=zg_bs_nav_electronics_1",
    "Electronics/Wearable Technology":"https://www.amazon.in/gp/bestsellers/electronics/11599648031/ref=zg_bs_nav_electronics_1",
    "Electronics/eBook Readers & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1389494031/ref=zg_bs_nav_electronics_1",
    "Garden & Outdoors/Backyard Birding & Wildlife":"https://www.amazon.in/gp/bestsellers/garden/3638771031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Backyard Birding Supplies":"https://www.amazon.in/gp/bestsellers/garden/3638784031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Backyard Livestock & Bee Care":"https://www.amazon.in/gp/bestsellers/garden/3638772031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Barbecue & Outdoor Dining":"https://www.amazon.in/gp/bestsellers/garden/3638773031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Beekeeping Equipment":"https://www.amazon.in/gp/bestsellers/garden/3638788031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Garden & Outdoor Furniture":"https://www.amazon.in/gp/bestsellers/garden/3638780031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Gardening":"https://www.amazon.in/gp/bestsellers/garden/3638775031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Heavy Equipment & Agricultural Supplies":"https://www.amazon.in/gp/bestsellers/garden/10448916031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Mowers & Outdoor Power Tools":"https://www.amazon.in/gp/bestsellers/garden/3638776031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Outdoor Décor":"https://www.amazon.in/gp/bestsellers/garden/3638777031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Outdoor Heaters & Fire Pits":"https://www.amazon.in/gp/bestsellers/garden/3638778031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Outdoor Storage & Housing":"https://www.amazon.in/gp/bestsellers/garden/3638779031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Pest Control":"https://www.amazon.in/gp/bestsellers/garden/3638816031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Plants, Seeds & Bulbs":"https://www.amazon.in/gp/bestsellers/garden/3638817031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Pools, Hot Tubs & Supplies":"https://www.amazon.in/gp/bestsellers/garden/3638781031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Snow Removal":"https://www.amazon.in/gp/bestsellers/garden/3638782031/ref=zg_bs_nav_garden_1",
    "Garden & Outdoors/Solar & Wind Power":"https://www.amazon.in/gp/bestsellers/garden/3639116031/ref=zg_bs_nav_garden_1",
    "Gift Cards/Anniversary":"https://www.amazon.in/gp/bestsellers/gift-cards/92070986031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Baby & Expecting":"https://www.amazon.in/gp/bestsellers/gift-cards/92070988031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Birthday":"https://www.amazon.in/gp/bestsellers/gift-cards/92070984031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Congratulations":"https://www.amazon.in/gp/bestsellers/gift-cards/92070987031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/For Occasions":"https://www.amazon.in/gp/bestsellers/gift-cards/92070989031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Friendship":"https://www.amazon.in/gp/bestsellers/gift-cards/92070985031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Get Well":"https://www.amazon.in/gp/bestsellers/gift-cards/92070981031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Gift Cards & Certificates":"https://www.amazon.in/gp/bestsellers/gift-cards/4048867031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Housewarming":"https://www.amazon.in/gp/bestsellers/gift-cards/92070982031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Love":"https://www.amazon.in/gp/bestsellers/gift-cards/92070980031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Thank You & Appreciation":"https://www.amazon.in/gp/bestsellers/gift-cards/92070979031/ref=zg_bs_nav_gift-cards_1",
    "Gift Cards/Wedding & Engagement":"https://www.amazon.in/gp/bestsellers/gift-cards/92070983031/ref=zg_bs_nav_gift-cards_1",
    "Grocery & Gourmet Foods/Bakery":"https://www.amazon.in/gp/bestsellers/grocery/4859474031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Breakfast Cereal":"https://www.amazon.in/gp/bestsellers/grocery/88365844031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Canned & Jarred Food":"https://www.amazon.in/gp/bestsellers/grocery/4859476031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Coffee, Tea & Beverages":"https://www.amazon.in/gp/bestsellers/grocery/4859478031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Cooking & Baking Supplies":"https://www.amazon.in/gp/bestsellers/grocery/4859479031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Dried Fruits, Nuts & Seeds":"https://www.amazon.in/gp/bestsellers/grocery/4859481031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Frozen":"https://www.amazon.in/gp/bestsellers/grocery/4859484031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Hampers & Gourmet Gifts":"https://www.amazon.in/gp/bestsellers/grocery/4859485031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Jams, Honey & Spreads":"https://www.amazon.in/gp/bestsellers/grocery/4859489031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Meat Subsitutes":"https://www.amazon.in/gp/bestsellers/grocery/4859677031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Meat, Poultry & Seafood":"https://www.amazon.in/gp/bestsellers/grocery/4859490031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Pasta & Noodles":"https://www.amazon.in/gp/bestsellers/grocery/4859494031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Pickles":"https://www.amazon.in/gp/bestsellers/grocery/4859492031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Ready To Eat & Cook":"https://www.amazon.in/gp/bestsellers/grocery/4859493031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Rice, Flour & Pulses":"https://www.amazon.in/gp/bestsellers/grocery/4859482031/ref=zg_bs_nav_grocery_1",
    "Grocery & Gourmet Foods/Snacks & Sweets":"https://www.amazon.in/gp/bestsellers/grocery/27966993031/ref=zg_bs_nav_grocery_1",
    "Health & Personal Care/Bath & Shower":"https://www.amazon.in/gp/bestsellers/hpc/1374276031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Diet & Nutrition":"https://www.amazon.in/gp/bestsellers/hpc/1374489031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Health Care":"https://www.amazon.in/gp/bestsellers/hpc/1374494031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Home Medical Supplies & Equipment":"https://www.amazon.in/gp/bestsellers/hpc/1374593031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Household Supplies":"https://www.amazon.in/gp/bestsellers/hpc/1374515031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Oral Care":"https://www.amazon.in/gp/bestsellers/hpc/1374620031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Personal Care":"https://www.amazon.in/gp/bestsellers/hpc/1374594031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Personal Care & Health Appliances":"https://www.amazon.in/gp/bestsellers/hpc/3150026031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Skin Care":"https://www.amazon.in/gp/bestsellers/hpc/1374407031/ref=zg_bs_nav_hpc_1",
    "Health & Personal Care/Tools & Accessories":"https://www.amazon.in/gp/bestsellers/hpc/1374450031/ref=zg_bs_nav_hpc_1",
    "Home & Kitchen/Coffee, Tea & Espresso":"https://www.amazon.in/gp/bestsellers/kitchen/1379960031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Cookware":"https://www.amazon.in/gp/bestsellers/kitchen/1380015031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Craft Materials":"https://www.amazon.in/gp/bestsellers/kitchen/10743065031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Fresh Flowers":"https://www.amazon.in/gp/bestsellers/kitchen/4297304031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Furniture":"https://www.amazon.in/gp/bestsellers/kitchen/1380441031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Heating & Cooling":"https://www.amazon.in/gp/bestsellers/kitchen/2083423031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Home & Décor":"https://www.amazon.in/gp/bestsellers/kitchen/1380374031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Home Furnishing":"https://www.amazon.in/gp/bestsellers/kitchen/1380442031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Home Improvement":"https://www.amazon.in/gp/bestsellers/kitchen/4286640031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Home Storage & Organization":"https://www.amazon.in/gp/bestsellers/kitchen/1380510031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Indoor Lighting":"https://www.amazon.in/gp/bestsellers/kitchen/1380485031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Kitchen & Dining":"https://www.amazon.in/gp/bestsellers/kitchen/5925789031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Kitchen Storage & Containers":"https://www.amazon.in/gp/bestsellers/kitchen/1379989031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Kitchen Tools":"https://www.amazon.in/gp/bestsellers/kitchen/1380181031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Large Appliances":"https://www.amazon.in/gp/bestsellers/kitchen/1380263031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Sewing & Embroidery Machines":"https://www.amazon.in/gp/bestsellers/kitchen/2083428031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Small Kitchen Appliances":"https://www.amazon.in/gp/bestsellers/kitchen/1380045031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Tableware":"https://www.amazon.in/gp/bestsellers/kitchen/1380098031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Vacuum, Cleaning & Ironing":"https://www.amazon.in/gp/bestsellers/kitchen/1380565031/ref=zg_bs_nav_kitchen_1",
    "Home & Kitchen/Water Purifiers & Accessories":"https://www.amazon.in/gp/bestsellers/kitchen/1380259031/ref=zg_bs_nav_kitchen_1",
    "Home Improvement/Building Supplies":"https://www.amazon.in/gp/bestsellers/home-improvement/10615970031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Cleaning Supplies":"https://www.amazon.in/gp/bestsellers/home-improvement/2083408031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Electrical":"https://www.amazon.in/gp/bestsellers/home-improvement/4286641031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Fireplaces & Gas Stoves":"https://www.amazon.in/gp/bestsellers/home-improvement/10616369031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Garage Storage & Organization":"https://www.amazon.in/gp/bestsellers/home-improvement/29594128031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Hardware":"https://www.amazon.in/gp/bestsellers/home-improvement/4286642031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Heavy Equipment & Agricultural Supplies":"https://www.amazon.in/gp/bestsellers/home-improvement/10448916031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Kitchen & Bath Fixtures":"https://www.amazon.in/gp/bestsellers/home-improvement/4286643031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Lighting Fixtures":"https://www.amazon.in/gp/bestsellers/home-improvement/202449866031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Painting Supplies, Tools & Wall Treatments":"https://www.amazon.in/gp/bestsellers/home-improvement/5745030031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Plumbing":"https://www.amazon.in/gp/bestsellers/home-improvement/10615921031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Power & Hand Tools":"https://www.amazon.in/gp/bestsellers/home-improvement/4286644031/ref=zg_bs_nav_home-improvement_1",
    "Home Improvement/Safety & Security":"https://www.amazon.in/gp/bestsellers/home-improvement/4286645031/ref=zg_bs_nav_home-improvement_1",
    "Industrial & Scientific/Abrasive & Finishing Products":"https://www.amazon.in/gp/bestsellers/industrial/6410388031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Additive Manufacturing Products":"https://www.amazon.in/gp/bestsellers/industrial/10616676031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Adhesives, Sealants and Lubricants":"https://www.amazon.in/gp/bestsellers/industrial/206246516031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Agricultural Equipment & Supplies":"https://www.amazon.in/gp/bestsellers/industrial/28179059031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Commercial Door Products":"https://www.amazon.in/gp/bestsellers/industrial/6306105031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Commercial Lighting":"https://www.amazon.in/gp/bestsellers/industrial/206246518031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Cutting Tools":"https://www.amazon.in/gp/bestsellers/industrial/6409856031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Digital Signage":"https://www.amazon.in/gp/bestsellers/industrial/206246517031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Education Supplies":"https://www.amazon.in/gp/bestsellers/industrial/206246515031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Fasteners":"https://www.amazon.in/gp/bestsellers/industrial/6761648031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Filtration":"https://www.amazon.in/gp/bestsellers/industrial/6410258031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Food Service Equipment & Supplies":"https://www.amazon.in/gp/bestsellers/industrial/7110888031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Hydraulics, Pneumatics & Plumbing":"https://www.amazon.in/gp/bestsellers/industrial/7355394031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Industrial Electrical":"https://www.amazon.in/gp/bestsellers/industrial/7355875031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Industrial Hardware":"https://www.amazon.in/gp/bestsellers/industrial/7355311031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Janitorial & Sanitation Supplies":"https://www.amazon.in/gp/bestsellers/industrial/6563520031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Lab & Scientific Products":"https://www.amazon.in/gp/bestsellers/industrial/6409335031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Material Handling Products":"https://www.amazon.in/gp/bestsellers/industrial/7110103031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Occupational Health & Safety Products":"https://www.amazon.in/gp/bestsellers/industrial/7110334031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Packaging & Shipping Supplies":"https://www.amazon.in/gp/bestsellers/industrial/11029528031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Power & Hand Tools":"https://www.amazon.in/gp/bestsellers/industrial/7355544031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Power Transmission Products":"https://www.amazon.in/gp/bestsellers/industrial/6395139031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Professional Dental Supplies":"https://www.amazon.in/gp/bestsellers/industrial/6410660031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Professional Medical Supplies":"https://www.amazon.in/gp/bestsellers/industrial/6395532031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Raw Materials":"https://www.amazon.in/gp/bestsellers/industrial/206246514031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Retail Store Fixtures & Equipment":"https://www.amazon.in/gp/bestsellers/industrial/22955924031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Robotics":"https://www.amazon.in/gp/bestsellers/industrial/10572875031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Science Education":"https://www.amazon.in/gp/bestsellers/industrial/6409937031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Tapes, Adhesives & Sealers":"https://www.amazon.in/gp/bestsellers/industrial/7124091031/ref=zg_bs_nav_industrial_1",
    "Industrial & Scientific/Test, Measure & Inspect":"https://www.amazon.in/gp/bestsellers/industrial/6395912031/ref=zg_bs_nav_industrial_1",
    "Jewellery/Boys":"https://www.amazon.in/gp/bestsellers/jewelry/7124360031/ref=zg_bs_nav_jewelry_1",
    "Jewellery/Girls":"https://www.amazon.in/gp/bestsellers/jewelry/7124361031/ref=zg_bs_nav_jewelry_1",
    "Jewellery/Men":"https://www.amazon.in/gp/bestsellers/jewelry/7124359031/ref=zg_bs_nav_jewelry_1",
    "Jewellery/Women":"https://www.amazon.in/gp/bestsellers/jewelry/7124358031/ref=zg_bs_nav_jewelry_1",
    "Kindle Store/Kindle eBooks":"https://www.amazon.in/gp/bestsellers/digital-text/1634753031/ref=zg_bs_nav_digital-text_1",
    "Movies & TV Shows/Action & Adventure":"https://www.amazon.in/gp/bestsellers/dvd/21360334031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Animation":"https://www.amazon.in/gp/bestsellers/dvd/21360335031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Comedy":"https://www.amazon.in/gp/bestsellers/dvd/21360336031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Crime & Thriller":"https://www.amazon.in/gp/bestsellers/dvd/21360337031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Documentary":"https://www.amazon.in/gp/bestsellers/dvd/21360338031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Drama":"https://www.amazon.in/gp/bestsellers/dvd/21360339031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Fantasy":"https://www.amazon.in/gp/bestsellers/dvd/21360343031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Fitness & Wellness":"https://www.amazon.in/gp/bestsellers/dvd/21360344031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Horror":"https://www.amazon.in/gp/bestsellers/dvd/21360345031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Kids & Family":"https://www.amazon.in/gp/bestsellers/dvd/21360346031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Military & War":"https://www.amazon.in/gp/bestsellers/dvd/21360347031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Music & Concerts":"https://www.amazon.in/gp/bestsellers/dvd/21360348031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Musicals":"https://www.amazon.in/gp/bestsellers/dvd/21360349031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Romance":"https://www.amazon.in/gp/bestsellers/dvd/21360352031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Science Fiction":"https://www.amazon.in/gp/bestsellers/dvd/21360353031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Special Interest":"https://www.amazon.in/gp/bestsellers/dvd/21360355031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Sports":"https://www.amazon.in/gp/bestsellers/dvd/21360356031/ref=zg_bs_nav_dvd_1",
    "Movies & TV Shows/Western":"https://www.amazon.in/gp/bestsellers/dvd/21360360031/ref=zg_bs_nav_dvd_1",
    "Music/Alternative & Indie":"https://www.amazon.in/gp/bestsellers/music/1375694031/ref=zg_bs_nav_music_1",
    "Music/Bhangra":"https://www.amazon.in/gp/bestsellers/music/1375855031/ref=zg_bs_nav_music_1",
    "Music/Blues":"https://www.amazon.in/gp/bestsellers/music/1375706031/ref=zg_bs_nav_music_1",
    "Music/Comedy & Spoken Word":"https://www.amazon.in/gp/bestsellers/music/1375721031/ref=zg_bs_nav_music_1",
    "Music/Country":"https://www.amazon.in/gp/bestsellers/music/1375724031/ref=zg_bs_nav_music_1",
    "Music/Dance & Electronic":"https://www.amazon.in/gp/bestsellers/music/1375734031/ref=zg_bs_nav_music_1",
    "Music/Devotional & Spiritual":"https://www.amazon.in/gp/bestsellers/music/1375846031/ref=zg_bs_nav_music_1",
    "Music/Easy Listening":"https://www.amazon.in/gp/bestsellers/music/1375742031/ref=zg_bs_nav_music_1",
    "Music/Film Songs":"https://www.amazon.in/gp/bestsellers/music/1375845031/ref=zg_bs_nav_music_1",
    "Music/Folk & Songwriter":"https://www.amazon.in/gp/bestsellers/music/1375745031/ref=zg_bs_nav_music_1",
    "Music/Ghazals":"https://www.amazon.in/gp/bestsellers/music/1375847031/ref=zg_bs_nav_music_1",
    "Music/Gospel":"https://www.amazon.in/gp/bestsellers/music/1375758031/ref=zg_bs_nav_music_1",
    "Music/Hard Rock & Metal":"https://www.amazon.in/gp/bestsellers/music/1375759031/ref=zg_bs_nav_music_1",
    "Music/Indi Pop":"https://www.amazon.in/gp/bestsellers/music/1375856031/ref=zg_bs_nav_music_1",
    "Music/Indian Classical":"https://www.amazon.in/gp/bestsellers/music/1375848031/ref=zg_bs_nav_music_1",
    "Music/International Music":"https://www.amazon.in/gp/bestsellers/music/1375844031/ref=zg_bs_nav_music_1",
    "Music/Jazz":"https://www.amazon.in/gp/bestsellers/music/1375774031/ref=zg_bs_nav_music_1",
    "Music/Kids' Music & Radio Plays":"https://www.amazon.in/gp/bestsellers/music/1375787031/ref=zg_bs_nav_music_1",
    "Music/Lounge & Fusion":"https://www.amazon.in/gp/bestsellers/music/1375853031/ref=zg_bs_nav_music_1",
    "Music/New Age":"https://www.amazon.in/gp/bestsellers/music/1375795031/ref=zg_bs_nav_music_1",
    "Music/Pop":"https://www.amazon.in/gp/bestsellers/music/1375796031/ref=zg_bs_nav_music_1",
    "Music/R&B & Soul":"https://www.amazon.in/gp/bestsellers/music/1375807031/ref=zg_bs_nav_music_1",
    "Music/Rap & Hip-Hop":"https://www.amazon.in/gp/bestsellers/music/1375814031/ref=zg_bs_nav_music_1",
    "Music/Reggae":"https://www.amazon.in/gp/bestsellers/music/1375821031/ref=zg_bs_nav_music_1",
    "Music/Rock":"https://www.amazon.in/gp/bestsellers/music/1375826031/ref=zg_bs_nav_music_1",
    "Music/Sound Effects & Nature":"https://www.amazon.in/gp/bestsellers/music/1375837031/ref=zg_bs_nav_music_1",
    "Music/Soundtracks & Musicals":"https://www.amazon.in/gp/bestsellers/music/1375838031/ref=zg_bs_nav_music_1",
    "Music/Sufi & Qawwali":"https://www.amazon.in/gp/bestsellers/music/1375854031/ref=zg_bs_nav_music_1",
    "Music/Western Classical":"https://www.amazon.in/gp/bestsellers/music/1375716031/ref=zg_bs_nav_music_1",
    "Musical Instruments/DJ & VJ Equipment":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654316031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/Drums & Percussion":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654317031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/General Music-Making Accessories":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654318031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/Guitars, Basses & Gear":"https://www.amazon.in/gp/bestsellers/musical-instruments/22162674031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/Karaoke Equipment":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654320031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/Microphones":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654321031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/PA & Stage":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654322031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/Piano & Keyboard":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654323031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/Recording & Computer":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654324031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/String Instruments":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654325031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/Synthesisers, Samplers & Digital Instruments":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654326031/ref=zg_bs_nav_musical-instruments_1",
    "Musical Instruments/Wind Instruments":"https://www.amazon.in/gp/bestsellers/musical-instruments/4654327031/ref=zg_bs_nav_musical-instruments_1",
    "Office Products/Calendars, Planners & Personal Organisers":"https://www.amazon.in/gp/bestsellers/office/3591015031/ref=zg_bs_nav_office_1",
    "Office Products/Office Electronics":"https://www.amazon.in/gp/bestsellers/office/3591018031/ref=zg_bs_nav_office_1",
    "Office Products/Office Paper Products":"https://www.amazon.in/gp/bestsellers/office/3591019031/ref=zg_bs_nav_office_1",
    "Office Products/Office Supplies":"https://www.amazon.in/gp/bestsellers/office/3591020031/ref=zg_bs_nav_office_1",
    "Pet Supplies/Birds":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771340031/ref=zg_bs_nav_pet-supplies_1",
    "Pet Supplies/Cats":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771341031/ref=zg_bs_nav_pet-supplies_1",
    "Pet Supplies/Dogs":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771342031/ref=zg_bs_nav_pet-supplies_1",
    "Pet Supplies/Fish & Aquatics":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771339031/ref=zg_bs_nav_pet-supplies_1",
    "Pet Supplies/Horses":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771343031/ref=zg_bs_nav_pet-supplies_1",
    "Pet Supplies/Insects":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771344031/ref=zg_bs_nav_pet-supplies_1",
    "Pet Supplies/Live Animals":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771345031/ref=zg_bs_nav_pet-supplies_1",
    "Pet Supplies/Reptiles & Amphibians":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771346031/ref=zg_bs_nav_pet-supplies_1",
    "Pet Supplies/Small Animals":"https://www.amazon.in/gp/bestsellers/pet-supplies/4771347031/ref=zg_bs_nav_pet-supplies_1",
    "Shoes & Handbags/Handbags, Purses & Clutches":"https://www.amazon.in/gp/bestsellers/shoes/1983338031/ref=zg_bs_nav_shoes_1",
    "Shoes & Handbags/Shoe Care & Accessories":"https://www.amazon.in/gp/bestsellers/shoes/1983320031/ref=zg_bs_nav_shoes_1",
    "Shoes & Handbags/Shoes":"https://www.amazon.in/gp/bestsellers/shoes/1983396031/ref=zg_bs_nav_shoes_1",
    "Software/Accounting & Finance":"https://www.amazon.in/gp/bestsellers/software/5490080031/ref=zg_bs_nav_software_1",
    "Software/Antivirus & Security":"https://www.amazon.in/gp/bestsellers/software/5490081031/ref=zg_bs_nav_software_1",
    "Software/Business & Office":"https://www.amazon.in/gp/bestsellers/software/5490082031/ref=zg_bs_nav_software_1",
    "Software/Children's Software":"https://www.amazon.in/gp/bestsellers/software/5490083031/ref=zg_bs_nav_software_1",
    "Software/Education & Reference":"https://www.amazon.in/gp/bestsellers/software/5490084031/ref=zg_bs_nav_software_1",
    "Software/Language & Travel":"https://www.amazon.in/gp/bestsellers/software/5490088031/ref=zg_bs_nav_software_1",
    "Software/Lifestyle & Hobbies":"https://www.amazon.in/gp/bestsellers/software/5490087031/ref=zg_bs_nav_software_1",
    "Software/Music":"https://www.amazon.in/gp/bestsellers/software/5490175031/ref=zg_bs_nav_software_1",
    "Software/Networking & Servers":"https://www.amazon.in/gp/bestsellers/software/5490090031/ref=zg_bs_nav_software_1",
    "Software/Operating Systems":"https://www.amazon.in/gp/bestsellers/software/5490091031/ref=zg_bs_nav_software_1",
    "Software/Photography & Graphic Design":"https://www.amazon.in/gp/bestsellers/software/5490086031/ref=zg_bs_nav_software_1",
    "Software/Programming & Web Development":"https://www.amazon.in/gp/bestsellers/software/5490093031/ref=zg_bs_nav_software_1",
    "Software/System Utility Software":"https://www.amazon.in/gp/bestsellers/software/5490094031/ref=zg_bs_nav_software_1",
    "Software/Tax Preparation":"https://www.amazon.in/gp/bestsellers/software/5490095031/ref=zg_bs_nav_software_1",
    "Software/Video":"https://www.amazon.in/gp/bestsellers/software/5490176031/ref=zg_bs_nav_software_1",
    "Sports, Fitness & Outdoors/Airsoft":"https://www.amazon.in/gp/bestsellers/sports/3403615031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/American Football":"https://www.amazon.in/gp/bestsellers/sports/3403616031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/American Handball":"https://www.amazon.in/gp/bestsellers/sports/3403617031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Archery":"https://www.amazon.in/gp/bestsellers/sports/3403618031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Badminton":"https://www.amazon.in/gp/bestsellers/sports/3403619031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Baseball":"https://www.amazon.in/gp/bestsellers/sports/3403620031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Basketball":"https://www.amazon.in/gp/bestsellers/sports/3403621031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Billiards":"https://www.amazon.in/gp/bestsellers/sports/3403622031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Bowling":"https://www.amazon.in/gp/bestsellers/sports/3403623031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Boxing":"https://www.amazon.in/gp/bestsellers/sports/3403624031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Cheerleading":"https://www.amazon.in/gp/bestsellers/sports/3403626031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Cricket":"https://www.amazon.in/gp/bestsellers/sports/3403628031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Cycling":"https://www.amazon.in/gp/bestsellers/sports/3403629031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Dance":"https://www.amazon.in/gp/bestsellers/sports/3403630031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Darts & Dartboards":"https://www.amazon.in/gp/bestsellers/sports/3403631031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Disc Sports":"https://www.amazon.in/gp/bestsellers/sports/3403632031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Equestrian Sports":"https://www.amazon.in/gp/bestsellers/sports/3403634031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Exercise & Fitness":"https://www.amazon.in/gp/bestsellers/sports/3403635031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Fencing":"https://www.amazon.in/gp/bestsellers/sports/3403637031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Field Hockey":"https://www.amazon.in/gp/bestsellers/sports/3403638031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Fishing":"https://www.amazon.in/gp/bestsellers/sports/3403639031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Football":"https://www.amazon.in/gp/bestsellers/sports/3403640031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Footwear":"https://www.amazon.in/gp/bestsellers/sports/3403641031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Futsal":"https://www.amazon.in/gp/bestsellers/sports/3403643031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Golf":"https://www.amazon.in/gp/bestsellers/sports/3403644031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Gymnastics":"https://www.amazon.in/gp/bestsellers/sports/3403646031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Hunting":"https://www.amazon.in/gp/bestsellers/sports/3403647031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Lacrosse":"https://www.amazon.in/gp/bestsellers/sports/3403649031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Martial Arts":"https://www.amazon.in/gp/bestsellers/sports/3403650031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Netball":"https://www.amazon.in/gp/bestsellers/sports/3403651031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Outdoor Recreation":"https://www.amazon.in/gp/bestsellers/sports/26063869031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Paddle Tennis":"https://www.amazon.in/gp/bestsellers/sports/3403652031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Polo Equipment":"https://www.amazon.in/gp/bestsellers/sports/3403654031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Racquetball":"https://www.amazon.in/gp/bestsellers/sports/3403655031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Rodeo":"https://www.amazon.in/gp/bestsellers/sports/3403656031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Roller Hockey":"https://www.amazon.in/gp/bestsellers/sports/3403657031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Rugby":"https://www.amazon.in/gp/bestsellers/sports/3403658031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Running":"https://www.amazon.in/gp/bestsellers/sports/3403659031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Skates, Skateboards & Scooters":"https://www.amazon.in/gp/bestsellers/sports/13831602031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Snooker":"https://www.amazon.in/gp/bestsellers/sports/3403663031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Soft Tennis":"https://www.amazon.in/gp/bestsellers/sports/3403664031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Softball":"https://www.amazon.in/gp/bestsellers/sports/3403665031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Sports":"https://www.amazon.in/gp/bestsellers/sports/100140618031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Sports & Outdoor Recreation Accessories":"https://www.amazon.in/gp/bestsellers/sports/12780048031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Sports Clothing":"https://www.amazon.in/gp/bestsellers/sports/3403666031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Sports Gadgets":"https://www.amazon.in/gp/bestsellers/sports/3403633031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Squash":"https://www.amazon.in/gp/bestsellers/sports/3403667031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Supporters' Gear":"https://www.amazon.in/gp/bestsellers/sports/3403636031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Table Tennis":"https://www.amazon.in/gp/bestsellers/sports/3403668031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Team Handball":"https://www.amazon.in/gp/bestsellers/sports/3403669031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Tennis":"https://www.amazon.in/gp/bestsellers/sports/3403670031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Track & Field":"https://www.amazon.in/gp/bestsellers/sports/3403671031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Triathlon":"https://www.amazon.in/gp/bestsellers/sports/3403672031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Trophies, Medals & Awards":"https://www.amazon.in/gp/bestsellers/sports/3403673031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Volleyball":"https://www.amazon.in/gp/bestsellers/sports/3403674031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Water Sports":"https://www.amazon.in/gp/bestsellers/sports/3403675031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Winter Sports":"https://www.amazon.in/gp/bestsellers/sports/3403676031/ref=zg_bs_nav_sports_1",
    "Sports, Fitness & Outdoors/Wrestling":"https://www.amazon.in/gp/bestsellers/sports/3403677031/ref=zg_bs_nav_sports_1",
    "Toys & Games/Arts & Crafts":"https://www.amazon.in/gp/bestsellers/toys/1378132031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Baby & Toddler Toys":"https://www.amazon.in/gp/bestsellers/toys/1378175031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Bikes, Trikes & Ride-Ons":"https://www.amazon.in/gp/bestsellers/toys/1378198031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Building & Construction Toys":"https://www.amazon.in/gp/bestsellers/toys/1378216031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Collectible Trading Cards & Accessories":"https://www.amazon.in/gp/bestsellers/toys/1378225031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Cooking Appliances":"https://www.amazon.in/gp/bestsellers/toys/1378489031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Dolls & Accessories":"https://www.amazon.in/gp/bestsellers/toys/1378260031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Dress-Up Accessories":"https://www.amazon.in/gp/bestsellers/toys/1378233031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Dressing Up & Costumes":"https://www.amazon.in/gp/bestsellers/toys/1378272031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Electronic Toys":"https://www.amazon.in/gp/bestsellers/toys/1378290031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Games":"https://www.amazon.in/gp/bestsellers/toys/1378311031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Learning & Education":"https://www.amazon.in/gp/bestsellers/toys/1378342031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Model Building Kits":"https://www.amazon.in/gp/bestsellers/toys/1378364031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Model Trains & Railway Sets":"https://www.amazon.in/gp/bestsellers/toys/1378384031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Musical Toy Instruments":"https://www.amazon.in/gp/bestsellers/toys/1378411031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Novelty & Gag Toys":"https://www.amazon.in/gp/bestsellers/toys/1378417031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Pretend Play":"https://www.amazon.in/gp/bestsellers/toys/1378451031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Puppets & Puppet Theatres":"https://www.amazon.in/gp/bestsellers/toys/1378463031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Puzzles":"https://www.amazon.in/gp/bestsellers/toys/1378470031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Remote & App-Controlled Toys":"https://www.amazon.in/gp/bestsellers/toys/1378480031/ref=zg_bs_nav_toys_1",
    "Toys & Games/School Supplies":"https://www.amazon.in/gp/bestsellers/toys/1378490031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Soft Toys":"https://www.amazon.in/gp/bestsellers/toys/1378445031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Sport & Outdoor":"https://www.amazon.in/gp/bestsellers/toys/1378509031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Toy Figures & Playsets":"https://www.amazon.in/gp/bestsellers/toys/1378568031/ref=zg_bs_nav_toys_1",
    "Toys & Games/Toy Vehicles":"https://www.amazon.in/gp/bestsellers/toys/1378242031/ref=zg_bs_nav_toys_1",
    "Video Games/Handheld Game Systems":"https://www.amazon.in/gp/bestsellers/videogames/92555865031/ref=zg_bs_nav_videogames_1",
    "Video Games/Legacy Systems":"https://www.amazon.in/gp/bestsellers/videogames/22713806031/ref=zg_bs_nav_videogames_1",
    "Video Games/Mac":"https://www.amazon.in/gp/bestsellers/videogames/14152496031/ref=zg_bs_nav_videogames_1",
    "Video Games/Nintendo Switch":"https://www.amazon.in/gp/bestsellers/videogames/13995115031/ref=zg_bs_nav_videogames_1",
    "Video Games/Nintendo Switch 2":"https://www.amazon.in/gp/bestsellers/videogames/206234396031/ref=zg_bs_nav_videogames_1",
    "Video Games/Online Game Services":"https://www.amazon.in/gp/bestsellers/videogames/14152570031/ref=zg_bs_nav_videogames_1",
    "Video Games/PC Games":"https://www.amazon.in/gp/bestsellers/videogames/1376518031/ref=zg_bs_nav_videogames_1",
    "Video Games/PlayStation 4":"https://www.amazon.in/gp/bestsellers/videogames/2591138031/ref=zg_bs_nav_videogames_1",
    "Video Games/PlayStation 5":"https://www.amazon.in/gp/bestsellers/videogames/20904621031/ref=zg_bs_nav_videogames_1",
    "Video Games/Xbox One":"https://www.amazon.in/gp/bestsellers/videogames/2785596031/ref=zg_bs_nav_videogames_1",
    "Video Games/Xbox Series X & S":"https://www.amazon.in/gp/bestsellers/videogames/20904638031/ref=zg_bs_nav_videogames_1",
    "Watches/Accessories":"https://www.amazon.in/gp/bestsellers/watches/1375486031/ref=zg_bs_nav_watches_1",
    "Watches/Boys":"https://www.amazon.in/gp/bestsellers/watches/2563506031/ref=zg_bs_nav_watches_1",
    "Watches/Girls":"https://www.amazon.in/gp/bestsellers/watches/5518819031/ref=zg_bs_nav_watches_1",
    "Watches/Men":"https://www.amazon.in/gp/bestsellers/watches/2563504031/ref=zg_bs_nav_watches_1",
    "Watches/Women":"https://www.amazon.in/gp/bestsellers/watches/2563505031/ref=zg_bs_nav_watches_1",
    "See More/Boys":"https://www.amazon.in/gp/bestsellers/jewelry/7124360031/ref=zg_bs_nav_jewelry_1",
    "See More/Girls":"https://www.amazon.in/gp/bestsellers/jewelry/7124361031/ref=zg_bs_nav_jewelry_1",
    "See More/Men":"https://www.amazon.in/gp/bestsellers/jewelry/7124359031/ref=zg_bs_nav_jewelry_1",
    "See More/Women":"https://www.amazon.in/gp/bestsellers/jewelry/7124358031/ref=zg_bs_nav_jewelry_1",
    "See More/Bath & Shower":"https://www.amazon.in/gp/bestsellers/beauty/1374276031/ref=zg_bs_nav_beauty_1",
    "See More/Fragrance":"https://www.amazon.in/gp/bestsellers/beauty/1374298031/ref=zg_bs_nav_beauty_1",
    "See More/Hair Care":"https://www.amazon.in/gp/bestsellers/beauty/9851597031/ref=zg_bs_nav_beauty_1",
    "See More/Make-up":"https://www.amazon.in/gp/bestsellers/beauty/1374357031/ref=zg_bs_nav_beauty_1",
    "See More/Manicure & Pedicure":"https://www.amazon.in/gp/bestsellers/beauty/27983606031/ref=zg_bs_nav_beauty_1",
    "See More/Skin Care":"https://www.amazon.in/gp/bestsellers/beauty/1374407031/ref=zg_bs_nav_beauty_1",
    "See More/Tools & Accessories":"https://www.amazon.in/gp/bestsellers/beauty/1374450031/ref=zg_bs_nav_beauty_1",
    "See More/Coffee, Tea & Espresso":"https://www.amazon.in/gp/bestsellers/kitchen/1379960031/ref=zg_bs_nav_kitchen_1",
    "See More/Cookware":"https://www.amazon.in/gp/bestsellers/kitchen/1380015031/ref=zg_bs_nav_kitchen_1",
    "See More/Craft Materials":"https://www.amazon.in/gp/bestsellers/kitchen/10743065031/ref=zg_bs_nav_kitchen_1",
    "See More/Fresh Flowers":"https://www.amazon.in/gp/bestsellers/kitchen/4297304031/ref=zg_bs_nav_kitchen_1",
    "See More/Furniture":"https://www.amazon.in/gp/bestsellers/kitchen/1380441031/ref=zg_bs_nav_kitchen_1",
    "See More/Heating & Cooling":"https://www.amazon.in/gp/bestsellers/kitchen/2083423031/ref=zg_bs_nav_kitchen_1",
    "See More/Home & Décor":"https://www.amazon.in/gp/bestsellers/kitchen/1380374031/ref=zg_bs_nav_kitchen_1",
    "See More/Home Furnishing":"https://www.amazon.in/gp/bestsellers/kitchen/1380442031/ref=zg_bs_nav_kitchen_1",
    "See More/Home Improvement":"https://www.amazon.in/gp/bestsellers/kitchen/4286640031/ref=zg_bs_nav_kitchen_1",
    "See More/Home Storage & Organization":"https://www.amazon.in/gp/bestsellers/kitchen/1380510031/ref=zg_bs_nav_kitchen_1",
    "See More/Indoor Lighting":"https://www.amazon.in/gp/bestsellers/kitchen/1380485031/ref=zg_bs_nav_kitchen_1",
    "See More/Kitchen & Dining":"https://www.amazon.in/gp/bestsellers/kitchen/5925789031/ref=zg_bs_nav_kitchen_1",
    "See More/Kitchen Storage & Containers":"https://www.amazon.in/gp/bestsellers/kitchen/1379989031/ref=zg_bs_nav_kitchen_1",
    "See More/Kitchen Tools":"https://www.amazon.in/gp/bestsellers/kitchen/1380181031/ref=zg_bs_nav_kitchen_1",
    "See More/Large Appliances":"https://www.amazon.in/gp/bestsellers/kitchen/1380263031/ref=zg_bs_nav_kitchen_1",
    "See More/Sewing & Embroidery Machines":"https://www.amazon.in/gp/bestsellers/kitchen/2083428031/ref=zg_bs_nav_kitchen_1",
    "See More/Small Kitchen Appliances":"https://www.amazon.in/gp/bestsellers/kitchen/1380045031/ref=zg_bs_nav_kitchen_1",
    "See More/Tableware":"https://www.amazon.in/gp/bestsellers/kitchen/1380098031/ref=zg_bs_nav_kitchen_1",
    "See More/Vacuum, Cleaning & Ironing":"https://www.amazon.in/gp/bestsellers/kitchen/1380565031/ref=zg_bs_nav_kitchen_1",
    "See More/Water Purifiers & Accessories":"https://www.amazon.in/gp/bestsellers/kitchen/1380259031/ref=zg_bs_nav_kitchen_1",
    "See More/Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1388867031/ref=zg_bs_nav_electronics_1",
    "See More/Cameras & Photography":"https://www.amazon.in/gp/bestsellers/electronics/1388977031/ref=zg_bs_nav_electronics_1",
    "See More/Car & Vehicle Electronics":"https://www.amazon.in/gp/bestsellers/electronics/1389221031/ref=zg_bs_nav_electronics_1",
    "See More/Computers & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1458204031/ref=zg_bs_nav_electronics_1",
    "See More/GPS & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1389315031/ref=zg_bs_nav_electronics_1",
    "See More/Headphones":"https://www.amazon.in/gp/bestsellers/electronics/1388921031/ref=zg_bs_nav_electronics_1",
    "See More/Hi-Fi & Home Audio":"https://www.amazon.in/gp/bestsellers/electronics/1389335031/ref=zg_bs_nav_electronics_1",
    "See More/Home Theatre, TV & Video":"https://www.amazon.in/gp/bestsellers/electronics/1389375031/ref=zg_bs_nav_electronics_1",
    "See More/Mobiles & Tablets":"https://www.amazon.in/gp/bestsellers/electronics/92071051031/ref=zg_bs_nav_electronics_1",
    "See More/Portable Media Players":"https://www.amazon.in/gp/bestsellers/electronics/1389433031/ref=zg_bs_nav_electronics_1",
    "See More/Radio Communication":"https://www.amazon.in/gp/bestsellers/electronics/1389462031/ref=zg_bs_nav_electronics_1",
    "See More/Telephones & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1389481031/ref=zg_bs_nav_electronics_1",
    "See More/Warranties":"https://www.amazon.in/gp/bestsellers/electronics/1389493031/ref=zg_bs_nav_electronics_1",
    "See More/Wearable Technology":"https://www.amazon.in/gp/bestsellers/electronics/11599648031/ref=zg_bs_nav_electronics_1",
    "See More/eBook Readers & Accessories":"https://www.amazon.in/gp/bestsellers/electronics/1389494031/ref=zg_bs_nav_electronics_1",
    "See More/Backyard Birding & Wildlife":"https://www.amazon.in/gp/bestsellers/garden/3638771031/ref=zg_bs_nav_garden_1",
    "See More/Backyard Birding Supplies":"https://www.amazon.in/gp/bestsellers/garden/3638784031/ref=zg_bs_nav_garden_1",
    "See More/Backyard Livestock & Bee Care":"https://www.amazon.in/gp/bestsellers/garden/3638772031/ref=zg_bs_nav_garden_1",
    "See More/Barbecue & Outdoor Dining":"https://www.amazon.in/gp/bestsellers/garden/3638773031/ref=zg_bs_nav_garden_1",
    "See More/Beekeeping Equipment":"https://www.amazon.in/gp/bestsellers/garden/3638788031/ref=zg_bs_nav_garden_1",
    "See More/Garden & Outdoor Furniture":"https://www.amazon.in/gp/bestsellers/garden/3638780031/ref=zg_bs_nav_garden_1",
    "See More/Gardening":"https://www.amazon.in/gp/bestsellers/garden/3638775031/ref=zg_bs_nav_garden_1",
    "See More/Heavy Equipment & Agricultural Supplies":"https://www.amazon.in/gp/bestsellers/garden/10448916031/ref=zg_bs_nav_garden_1",
    "See More/Mowers & Outdoor Power Tools":"https://www.amazon.in/gp/bestsellers/garden/3638776031/ref=zg_bs_nav_garden_1",
    "See More/Outdoor Décor":"https://www.amazon.in/gp/bestsellers/garden/3638777031/ref=zg_bs_nav_garden_1",
    "See More/Outdoor Heaters & Fire Pits":"https://www.amazon.in/gp/bestsellers/garden/3638778031/ref=zg_bs_nav_garden_1",
    "See More/Outdoor Storage & Housing":"https://www.amazon.in/gp/bestsellers/garden/3638779031/ref=zg_bs_nav_garden_1",
    "See More/Pest Control":"https://www.amazon.in/gp/bestsellers/garden/3638816031/ref=zg_bs_nav_garden_1",
    "See More/Plants, Seeds & Bulbs":"https://www.amazon.in/gp/bestsellers/garden/3638817031/ref=zg_bs_nav_garden_1",
    "See More/Pools, Hot Tubs & Supplies":"https://www.amazon.in/gp/bestsellers/garden/3638781031/ref=zg_bs_nav_garden_1",
    "See More/Snow Removal":"https://www.amazon.in/gp/bestsellers/garden/3638782031/ref=zg_bs_nav_garden_1",
    "See More/Solar & Wind Power":"https://www.amazon.in/gp/bestsellers/garden/3639116031/ref=zg_bs_nav_garden_1"
}

def generate_tags(name, specs):
    base_tags = ["AmazonFinds", "CoolGadgets", "AmazonIndia"]
    keywords = [w for w in name.split() if len(w) > 4][:6]
    return ", ".join(list(set(base_tags + keywords)))

def get_bestsellers(driver, count):

    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    
    cat_name, cat_url = random.choice(list(CATEGORIES.items()))
    print(f"🎲 Randomly selected category: {cat_name}")
    
    driver.get(cat_url)
    time.sleep(30)
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

            driver.set_window_size(1920, 1080)
            
            driver.get(link)
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, 350);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            img_paths = []
            high_res_urls = []
            thumbs = []

            try:
                # Target the main product display image
                main_img = driver.find_element(By.ID, "landingImage")
                dyn_img_attr = main_img.get_attribute("data-a-dynamic-image")
                
                if dyn_img_attr:
                    # data-a-dynamic-image contains a JSON string like: {"URL_1": [width, height], "URL_2": [...]}
                    dyn_data = json.loads(dyn_img_attr)
                    # Sort or pick keys (which are the image URLs)
                    high_res_urls = list(dyn_data.keys())
                    print(f"📸 Strategy 1: Extracted {len(high_res_urls)} assets from landingImage dynamic matrix.")
            except Exception as e:
                print(f"⚠️ Strategy 1 failed or bypassed: {e}")

            # --- STRATEGY 2: Inline Script JSON Parser Fallback ---
            if not high_res_urls:
                try:
                    page_source = driver.page_source
                    image_data_match = re.search(r'\'colorImages\':\s*\{\s*\'initial\':\s*(\[.+?\])', page_source)
                    if image_data_match:
                        image_json = json.loads(image_data_match.group(1))
                        high_res_urls = [img.get('hiRes') or img.get('large') for img in image_json if img]
                        high_res_urls = [url for url in high_res_urls if url]
                        print(f"📸 Strategy 2: Extracted {len(high_res_urls)} assets via inline layout script.")
                except Exception as e:
                    print(f"⚠️ Strategy 2 failed: {e}")

            # --- STRATEGY 3: Alt Thumbnails Raw Scraping (Final Fallback) ---
            if not high_res_urls:
                try:
                    thumbs = driver.find_elements(By.CSS_SELECTOR, "#altImages img, #altimages img, .imgTagWrapper img")
                    for img in thumbs:
                        src = img.get_attribute("data-old-hires") or img.get_attribute("src")
                        if src and not src.startswith("data:"):
                            # Normalize low-res thumbnail links to full resolution
                            clean_url = re.sub(r'\._[A-Z0-9_-]+\.', '.', src)
                            if clean_url not in high_res_urls:
                                high_res_urls.append(clean_url)
                    print(f"📸 Strategy 3: Collected {len(high_res_urls)} raw asset paths from visible tags.")
                except Exception as e:
                    print(f"⚠️ Strategy 3 failed: {e}")

            # --- DOWNLOAD PROCESSOR ---
            found = 0
            for idx, high_res in enumerate(high_res_urls):
                if found >= 7: break
                
                # Filter out obvious utility/video files
                if any(x in high_res.lower() for x in ["video", "play-button", "gif", "icon"]):
                    continue
                    
                try:
                    local_file = os.path.join(os.getcwd(), f"temp_{i}_{idx}.jpg")
                    
                    # Spoof headers clearly to match your Selenium session profile
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')]
                    urllib.request.install_opener(opener)
                    
                    urllib.request.urlretrieve(high_res, local_file)
                    if os.path.getsize(local_file) > 1000:
                        img_paths.append(local_file)
                        found += 1
                except Exception as e:
                    print(f"❌ Download failed for {high_res}: {e}")

            bullets = driver.find_elements(By.CSS_SELECTOR, "#feature-bullets ul li span, #pqv-feature-bullets ul li span")
            specs = " | ".join([b.text.strip() for b in bullets if len(b.text.strip()) > 10][:7])
            
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
        specs = " | ".join([b.text.strip() for b in bullets if len(b.text.strip()) > 10][:3])
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
            
                # 1. Pull the element attributes
                alt_text = (img.get_attribute("alt") or "").strip().lower()
                src = img.get_attribute("data-old-hires") or img.get_attribute("src")
                
                if not src:
                    continue

                # 🚀 STRICT FILTER: Drop video cards based on explicit text values or thumbnail decorations
                if "video" in alt_text:
                    print(f"⏭️ Skipping element {idx}: Matched alt label '{img.get_attribute('alt')}'")
                    continue
                    
                if any(x in src for x in ["play-button", "gif", "inline-twister", "video-placeholder", "play-icon-overlay","png"]):
                    print(f"⏭️ Skipping element {idx}: Detected video/interactive decoration string in URL")
                    continue
                                    
                # 2. Convert thumbnail asset signature into clean, full-resolution image path
                high_res = src
                if "._S" in src:
                    high_res = src.split("._S")[0] + ".jpg"
                elif "._" in src:
                    high_res = src.split("._")[0] + ".jpg"
                    
                try:
                    local_file = os.path.join(os.getcwd(), f"Manual_temp_{idx}.jpg")
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')]
                    urllib.request.install_opener(opener)                    
                    urllib.request.urlretrieve(high_res, local_file)                    
                    if os.path.getsize(local_file) > 1000: # Ensure it's a real valid image
                        img_paths.append(local_file)
                        found += 1
                except Exception as e:
                    print(f"❌ Download failed: {e}")
        
        return {
            "asin": asin,
            "name": name,
            "link": f"https://www.amazon.in/dp/{asin}?tag={os.getenv('Affiliate_Code')}",
            "price": price,
            "specs": specs,
            "images": img_paths
        }
    except Exception as e:
        print(f"❌ Manual Scrape Failed: {e}")
        return None