#!/usr/bin/env python

# Really early initial implementation of game info grabber - there will be tons of bugs, beware
# MCn

from bs4 import BeautifulSoup
import requests
import html5lib
import sys, re, json

# Codes used in search urls on MobyGames - add more if necessary
MG_CONSOLE_CODES = {'pc': 3, 'gb': 10, 'gbc': 11, 'gba': 12}
MG_CONSOLE_SLUGS = {'N64': 'N64', 'GBA': 'gameboy-advance', 'GBC': 'gameboy-color', 'Dreamcast': 'Dreamcast', 'gamecube': 'gamecube', 'Xbox': 'xbox', 'xbox360': 'xbox360', 'Wii U': 'Wii-u', 'Ps2': 'PS2', 'PS3': 'Ps3','Ps1': 'Playstation', 'genesis': 'genesis', 'android': 'android', 'PC': 'windows', 'nes': 'nes', '3ds': '3ds', 'DS': 'nintendo-ds', 'DSI': 'nintendo-dsi', 'snes': 'snes', 'iphone': 'iphone', 'wii': 'wii', 'mac':'macintosh', 'gameboy': 'gameboy'}


def upload_image(url):
    try:
        # dealing with pesky relative url
        if not 'http://' in url:
            url = 'https://www.mobygames.com/' + url
        # Check for weird url bug where sometimes the image would have two http://
        if '/https://' or '/http://' in url:
            url = url[len('https://www.mobygames.com/'):]
        # Remove double slashes
        url = url.replace('com//', 'com/')
        headers = {"Authorization": "Client-ID d656b9b04c8ff24"}
        params = {"image": url}
        r = requests.post("https://api.imgur.com/3/image", headers = headers, params = params)
        return json.loads(r.content)["data"]["link"]
    except:
        return ''

# Get URL if none supplied
if "http" in sys.argv[1]:
    game_page = sys.argv[1]
    game_name = ""
else:
    game_name = sys.argv[1]

    # Remove spaces and lowercase console name
    console = '-'.join(sys.argv[2].split()).lower()

    url_friendly_gn = ''.join(e for e in game_name.lower() if e.isalnum() or e == ' ').replace(' ', '-')

    # Try naive search with console
    if console in MG_CONSOLE_SLUGS:
        console_slug = format(MG_CONSOLE_SLUGS['console'])
    else:
        console_slug = console
    game_page = 'https://www.mobygames.com/game/{0}/{1}'.format(console_slug, url_friendly_gn)
    naive_soup = BeautifulSoup(requests.get(game_page).text.encode('utf-8'), 'html5lib')

    if not naive_soup.find('h1', class_='gameHeader'):
        # Try naive search without console
        game_page = 'https://www.mobygames.com/game/{0}'.format(url_friendly_gn)
        naive_soup = BeautifulSoup(requests.get(game_page).text.encode('utf-8'), 'html5lib')

        if not naive_soup.find('h1', class_='gameHeader'):
            # NEED TO SEARCH :(
            if console in MG_CONSOLE_CODES:
                console_code = MG_CONSOLE_CODES[console]
            else:
                console_code = -1

            # Search MobyGames for games
            search_url = 'https://www.mobygames.com/search/quick?q={0}&p={1}&search=Go&sFilter=1&sG=on'.format(game_name, console_code)
            search_soup = BeautifulSoup(requests.get(search_url).text)

            # # Find the page for the game
            game_page = search_soup.find("div", class_="searchResult").a.get('href')

# Open URL, need html5lib since default parser breaks on mobygames
soup = BeautifulSoup(requests.get(game_page).text, "html5lib")

# Source and language args
try:
    source = sys.argv[3]
except:
    source = None

try:
    language = sys.argv[4]
except:
    language = None

proper_game_title = soup.find('div', id='gameTitle').get_text()

game_release_div = soup.find('div', id='coreGameRelease')
date = game_release_div.find('div', text='Released').next_sibling.get_text()

game_genre_div = soup.find('div', id='coreGameGenre')
# NOTE: u'\xa0' is &nbsp; - remove it
genre = game_genre_div.find('div', text='Genre').next_sibling.get_text().replace(u'\xa0', '')

review = game_page + '/mobyrank'

description_div = soup.find('div', class_='rightPanelMain')
for br in description_div.findAll('br'):
    br.replace_with('\n')
string = description_div.get_text().encode('utf-8')
description_text = string[len('Description'):string.find('[edit description')]

# Get box art
game_box_data = soup.find("div", id="coreGameCover").img
if game_box_data:
    img_url = game_box_data.get("src").encode('utf-8').replace('small', 'large')
    imgur_game_box_url = upload_image(img_url)
else:
    imgur_game_box_url = None

# Get screenshots
screenshot_gallery_url = game_page + '/screenshots'
screenshot_soup = BeautifulSoup(requests.get(screenshot_gallery_url).text, "html5lib")
screenshot_images = screenshot_soup.find('div', class_='rightPanelMain').findAll('img')
screenshot_one_url, screenshot_two_url = None, None
if len(screenshot_images) > 0:
    screenshot_one_url = upload_image(screenshot_images[0].get('src').replace('/s/', '/l/'))
if len(screenshot_images) > 1:
    screenshot_two_url = upload_image(screenshot_images[1].get('src').replace('/s/', '/l/'))

# Print everything
print "Game Name: " + proper_game_title.encode('utf-8')
print "Released: " + date.encode('utf-8')
if source:
    print "Source: " + source.encode('utf-8')
if language:
    print "Language: " + language.encode('utf-8')
print "Game Genre: " + genre.encode('utf-8') + "\n"

print "[b]Review:[/b] " + review.encode('utf-8') + "\n"

print "[b]Description:[/b] "
print "[quote]"
print description_text
print "[/quote]"
print ""

# Emulator Suggestion
if sys.argv[2] == "PS1":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is EPSXE."
    print "http://www.epsxe.com/download.php[/quote]"
elif sys.argv[2] == "PS2":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is PCSX2."
    print "http://pcsx2.net/download.html[/quote]"
elif sys.argv[2] == "NES":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is FCEUX."
    print "http://www.fceux.com/web/home.html[/quote]"
elif sys.argv[2] == "SNES":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is ZSNES."
    print "http://www.zsnes.com/index.php?page=files[/quote]"
elif sys.argv[2] == "N64":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is Project 64."
    print "http://www.pj64-emu.com/[/quote]"
elif sys.argv[2] == "GB":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is Virtual Boy Advanced."
    print "http://vba.ngemu.com/downloads.shtml[/quote]"
elif sys.argv[2] == "GBC":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is Virtual Boy Advanced."
    print "http://vba.ngemu.com/downloads.shtml[/quote]"
elif sys.argv[2] == "GBA":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is Virtual Boy Advanced."
    print "http://vba.ngemu.com/downloads.shtml[/quote]"
elif sys.argv[2] == "GC":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is Dolphin."
    print "http://www.dolphin-emulator.com/download.html[/quote]"
elif sys.argv[2] == "WII":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is Dolphin."
    print "http://www.dolphin-emulator.com/download.html[/quote]"
elif sys.argv[2] == "DS":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is DSEmu."
    print "http://dsemu.oopsilon.com/[/quote]"
elif sys.argv[2] == "DOS":
    print "[b]Emulation:[/b]"
    print "[quote]The best Emulator to use is DOSBox."
    print "http://www.dosbox.com/download.php?main=1[/quote]"

if screenshot_one_url:
    print "\n[b]Screenshots:[/b]\n"
    print "[img]{0}[/img]".format(screenshot_one_url)
if screenshot_two_url:
    print "[img]{0}[/img]".format(screenshot_two_url)
if screenshot_one_url:
    print "Screenshot gallery: " + screenshot_gallery_url

if imgur_game_box_url:
    print "\n\nCover image: " + imgur_game_box_url

print "\n-------------------------------------------------\n"