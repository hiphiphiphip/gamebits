#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Usage:
  mGamebits.py <game> -f <format> [-l <language>] [-c <console>]
               [--no-screenshots]
  mGamebits.py --list-platforms
  mGamebits.py (-h | --help)
  mGamebits.py (-v | --version)

Creates pretty printed bbcode for games.

Options:
  -h --help
  -v --version

  --list-platforms                     List supported consoles.
  -f FORMAT --format=FORMAT            Game format.
  -l LANGUAGE --language=LANGUAGE      Game Language. Default is English.
  -c CONSOLE --console=CONSOLE         Game platform. Defaults to PC.
  --no-screenshots                     Don't take screenshots.

Examples:
  mGamebits.py "Command and Conquer" -f ISO
  mGamebits.py "Pokemon Red" -f ROM -c GB
  mGamebits.py "https://www.mobygames.com/game/playstation/metal-gear-solid" -f ISO
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from collections import namedtuple
from functools import partial
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO  # py3k
from pprint import pprint

import requests
from bs4 import BeautifulSoup as bs
from docopt import docopt


TEMPLATE_MAIN = """\
Game Name: {title}
Released: {date}
Source: {source}
Language: {language}
Game Genre: {genre}

[b]Review:[/b]
{review}

[b]Description[/b]
[quote]
{description}
[/quote]

"""

TEMPLATE_EMULATOR = """\
[b]Emulation:[/b]
[quote]
The best emulator to use is {emulator}.
{link}
[/quote]

"""

TEMPLATE_IMAGES = """\
[b]Screenshots[/b]
{screenshots}
Screenshot gallery: {gallery}

Cover image: {cover}
"""

_info = namedtuple('info', ('emulator', 'link', 'id'))
CONSOLE_TO_EMULATOR_MAP = {
    'PS1': _info('EPSXE',
                 'http://www.epsxe.com/download.php',
                 6),
    'PS2': _info('PCSX2',
                 'http://pcsx2.net/download.html',
                 7),
    'NES': _info('FCEUX',
                 'http://www.fceux.com/web/home.html',
                 22),
    'SNES': _info('ZSNES',
                  'http://www.zsnes.com/index.php?page=files',
                  15),
    'N64': _info('Project 64',
                 'http://www.pj64-emu.com/',
                 9),
    'GB': _info('Virtual Boy Advanced',
                'http://vba.ngemu.com/downloads.shtml',
                10),
    'GBC': _info('Virtual Boy Advanced',
                 'http://vba.ngemu.com/downloads.shtml',
                 11),
    'GBA': _info('Virtual Boy Advanced',
                 'http://vba.ngemu.com/downloads.shtml',
                 12),
    'GC': _info('Dolphin',
                'http://www.dolphin-emulator.com/download.html',
                14),
    'WII': _info('The best Emulator to use is Dolphin.',
                 'http://www.dolphin-emulator.com/download.html',
                 82),
    'DS': _info('DSEmu',
                'http://dsemu.oopsilon.com/',
                44),
    'DOS': _info('DOSBox',
                 'http://www.dosbox.com/download.php?main=1',
                 2)}


def upload_from_url(url):
    return url


class GameNotFoundError(Exception):
    pass


class MobyGetter(object):
    BASE_URL = 'https://www.mobygames.com'
    HEADERS = {'user-agent': 'PrettyPrinter/1.0.0'}

    get = partial(requests.get,
                  headers=HEADERS)

    @classmethod
    def make_absolute(cls, relative_url):
        return cls.BASE_URL + relative_url


class Screenshots(MobyGetter):
    RESOURCE = '/screenshots'

    def __init__(self, url, number=3):
        self.url = url + self.RESOURCE
        self.number = number

    def urls(self):
        response = self.get(self.url)
        if not response.ok:
            raise GameNotFoundError(
                "Can't get screenshots at  %s" % self.url)
        return self._extract_image_urls(bs(response.content))

    def _extract_image_urls(self, tree):
        urls = [a['style'] for a in
                tree.select('a.thumbnail-image')][:self.number]
        # clean string looking like 'background-image:url(RELATIVE_URL);'
        urls = [url.split('(', 1)[1].split(')', 1)[0] for url in urls]
        # thumbnail => full
        urls = [self.thumbnail_to_full(url) for url in urls]
        # relative => absolute
        return [self.make_absolute(url) for url in urls]

    @staticmethod
    def thumbnail_to_full(thumbnail_url):
        return thumbnail_url.replace('/s/', '/l/')


class Game(MobyGetter):
    def __init__(self, url):
        self.url = url
        response = self.get(url)
        if not response.ok:
            raise GameNotFoundError('Could not get url %s' % url)
        self.tree = bs(response.content)

    @property
    def title(self):
        return self.tree.select('h1.niceHeaderTitle a')[0].text

    @property
    def screenshots(self):
        return Screenshots(self.url).urls()

    @property
    def description(self):
        main_text = self.tree.select('.col-md-8.col-lg-8')[0]

        for br in main_text.select('br'):
            br.replaceWith('\n')
        main_text = main_text.text

        try:
            description, __ = main_text.split('[edit description')
        except ValueError:
            description, __ = main_text.split('[more descriptions')

        return description.split('Description', 1)[1].strip()

    @property
    def genre(self):
        return self.tree.select('#coreGameGenre a')[0].text

    @property
    def released(self):
        return self.tree.select('#coreGameRelease '
                                'a[href*="release-info"]')[0].text

    @property
    def cover(self):
        thumbnail = self.tree.select('#coreGameCover img')[0]['src']
        return thumbnail.replace('/small/', '/large/')

    @property
    def review(self):
        return self.url + '/mobyrank'

    @property
    def gallery(self):
        return self.url + '/screenshots'


class MobyGames(MobyGetter):
    def __init__(self):
        pass

    def search(self, name, console=None):
        RESOURCE = '/search/quick'

        params = {'q': name}
        if console:
            try:
                mobygames_console_id = CONSOLE_TO_EMULATOR_MAP[console].id
            except KeyError:
                raise GameNotFoundError(
                    "I don't know the correct console code for '{}'. "
                    "Try again without specifying the console."
                    .format(console))
            params['p'] = mobygames_console_id

        response = self.get(self.BASE_URL + RESOURCE,
                            params=params)
        if not response.ok:
            raise GameNotFoundError(response.request_url)

        url = self._extract_result(response.content)
        return Game(url)

    @staticmethod
    def _extract_result(content):
        tree = bs(content)

        game_a_elements = tree.select('#searchResults '
                                      '.searchSubSection '
                                      '.searchResult '
                                      '.searchTitle '
                                      'a')
        game_urls = [a['href'] for a in
                     game_a_elements]
        if game_urls:
            return game_urls[0]  # most precise match
        else:
            raise GameNotFoundError('No matching urls found')


class ImageUploadError(Exception):
    pass


def upload(url):
    BASE_URL = 'https://images.baconbits.org'

    try:
        j = requests.post(BASE_URL + '/upload.php',
                          data={'url': url}).json()
    except ValueError:
        raise ImageUploadError("Failed to upload '%s'!" % url)

    if 'ImgName' in j:
        return BASE_URL + '/images/' + j['ImgName']
    else:
        raise ImageUploadError("Failed to upload '%s'!" % url,
                               repr(j))


def is_url(s):
    if any(s.startswith(substr) for substr in ('http://', 'https://')):
        return True
    else:
        return False


def main(name, format, language, console, no_screenshots):
    out = StringIO()  # print everything at the end

    if is_url(name):
        g = Game(name)
    else:
        g = MobyGames().search(name, console)

    print(TEMPLATE_MAIN.format(title=g.title,
                               date=g.released,
                               source=format,
                               language=language,
                               genre=g.genre,
                               review=g.review,
                               description=g.description),
          file=out)

    if console:
        emu = CONSOLE_TO_EMULATOR_MAP.get(console.upper(), None)
        if not emu:
            raise ValueError('Unknown Console %s' % console)
        print(TEMPLATE_EMULATOR.format(link=emu.link,
                                       emulator=emu.emulator),
              file=out)

    if not no_screenshots:
        screenshots = "\n".join("[img]{}[/img]".format(upload(url))
                                for url in g.screenshots)

        print(TEMPLATE_IMAGES.format(
            screenshots=screenshots,
            gallery=g.gallery,
            cover=upload(g.cover)), file=out)

    print('-' * 80, file=out)
    print(out.getvalue())


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Pythonbits {}'.format('1.0.1'))
    defaults = {'console': None, 'language': 'English'}

    if arguments['--list-platforms']:
        pprint(CONSOLE_TO_EMULATOR_MAP)
        exit(0)

    main(arguments['<game>'],
         arguments['--format'],
         arguments['--language'] or defaults['language'],
         arguments['--console'] or defaults['console'],
         arguments['--no-screenshots'])
