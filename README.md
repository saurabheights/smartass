# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/saurabheights/smartass/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                               |    Stmts |     Miss |   Cover |   Missing |
|----------------------------------- | -------: | -------: | ------: | --------: |
| smartass/\_\_init\_\_.py           |        1 |        0 |    100% |           |
| smartass/core/config.py            |       88 |       17 |     81% |14, 41-52, 68, 75-77, 97-100, 109-110, 145, 151-152 |
| smartass/core/dbus\_names.py       |       11 |        2 |     82% |    16, 20 |
| smartass/core/manifest.py          |       56 |       11 |     80% |12, 50, 53-54, 58, 62, 66, 72, 78, 82, 87 |
| smartass/core/paths.py             |       32 |       12 |     62% |16-21, 25, 33, 37, 41, 49, 54, 59-67 |
| smartass/core/plugin\_interface.py |      126 |       27 |     79% |33, 50, 52, 65, 67, 69, 73-76, 85-87, 98, 100, 104-106, 115-117, 137, 147, 171-172, 221, 229 |
| smartass/daemon/\_\_main\_\_.py    |       60 |       60 |      0% |      3-89 |
| smartass/daemon/http.py            |       12 |        3 |     75% | 19-20, 23 |
| smartass/daemon/plugin\_manager.py |      146 |       38 |     74% |61, 64-66, 68-69, 76, 81, 86, 91-93, 96, 105, 108, 130-131, 134, 143-145, 159-163, 177-184, 188-191 |
| smartass/daemon/plugin\_object.py  |       23 |        7 |     70% |     29-36 |
| smartass/daemon/service.py         |      162 |       92 |     43% |11, 72, 80-106, 110-111, 115-133, 141-166, 170-172, 176, 182, 196, 200, 206, 212, 219-234, 238-244, 248, 252-264 |
| smartass/plugins/weather/api.py    |       77 |       22 |     71% |77-82, 93-163 |
| smartass/plugins/weather/plugin.py |       88 |       88 |      0% |     3-187 |
| smartass/plugins/weather/ui.py     |      224 |      224 |      0% |     7-373 |
| smartass/tray/\_\_main\_\_.py      |       21 |       21 |      0% |      4-33 |
| smartass/tray/app.py               |       55 |       55 |      0% |      4-98 |
| smartass/tray/daemon\_client.py    |       62 |       62 |      0% |     9-107 |
| smartass/tray/main\_window.py      |       90 |       90 |      0% |     4-125 |
| smartass/tray/schema\_form.py      |       75 |       75 |      0% |     4-108 |
| smartass/tray/settings\_tab.py     |      104 |      104 |      0% |     4-142 |
| smartass/tray/tray\_icon.py        |       25 |       25 |      0% |      4-43 |
| **TOTAL**                          | **1538** | **1035** | **33%** |           |

5 empty files skipped.


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/saurabheights/smartass/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/saurabheights/smartass/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/saurabheights/smartass/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/saurabheights/smartass/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fsaurabheights%2Fsmartass%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/saurabheights/smartass/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.