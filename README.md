<img src="docs/img/logo.svg" alt="logo" style="zoom:50%;" />



[![Built with Material for MkDocs](https://img.shields.io/badge/Material_for_MkDocs-526CFE?style=for-the-badge&logo=MaterialForMkDocs&logoColor=white)](https://nathanreitinger.github.io/CART/)



# Culling Abstacts for Relevancy in Teams

`CART` provides a way for teams of researchers to "cull" through a large set of papers when conducting a systematic review—also known as an "SoK." `CART` uses `ngrok` (a free service for temporary website creation), to zero-step the startup time for collaborative relevancy checking. 

### Documentation

Documentation for `CART` is available on [Read the Docs](https://nathanreitinger.github.io/CART/).

### Demo

<video controls src="docs/img/demo.mov"></video>



### Repo Structure 

```
.
├── LICENSE.txt
├── README.md
├── abstracts                  // papers as <ID>.csv go here
│   ├── -example_data_big      // example papers (many of them!)
│   │   ├── 1.csv              // formatted as <ID>.csv (ID like primary key)
│   │   ├── ...								
│   │   └── 99.csv							
│   ├── -example_data_small    // example papers (few of them!)
│   │   ├── 1.csv
│   │   ├── ...
│   │   └── 5.csv
│   ├── -sample_from_scrape/   // folder output for get_data.py 
│   └── -testing               // folder used by test.py to run tests
├── cart.py                    // *************** main program *************** // 
├── docs/                      // documentation for readthedocs
├── info/                      // "about" tab for information on relevancy assessment
├── mkdocs.yml                 // readthedocs
├── paper.md                   // JOSS
├── requirements.txt           // install dependencies 
├── sample_get_data/get_data.py// web scraper to populate sample paper data 
├── static/                    // images and CSS for web
├── templates                  // web page HTML files
│   ├── history.html           // past n abstracts you voted on (can change vote)
│   ├── index.html             // home (gamified voting experience)
│   ├── info.html              // "about" page editable by team members
│   ├── progress.html          // total votes cast and who cast them
│   └── start.html             // "account" page for login and logout 
└── testing/test.py            // testing scripts for `CART` app 

```



