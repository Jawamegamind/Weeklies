# 🍽️ WEEKLIES — Intelligent Meal Planning and Delivery System

[![CI](https://github.com/Jawamegamind/Weeklies/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Jawamegamind/Weeklies/actions/workflows/ci.yml)
[![Docs](https://github.com/Jawamegamind/Weeklies/actions/workflows/docs.yml/badge.svg?branch=main&event=push)](https://github.com/Jawamegamind/Weeklies/actions/workflows/docs.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
![Tests](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/Jawamegamind/0ab63df1c29ad707ee2f0c5bdbf46383/raw/tests-badge.json)
[![codecov](https://codecov.io/gh/Jawamegamind/Weeklies/branch/main/graph/badge.svg)](https://codecov.io/gh/Jawamegamind/Weeklies)
[![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/github/license/Jawamegamind/Weeklies.svg)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/Jawamegamind/Weeklies.svg)](https://github.com/Jawamegamind/Weeklies/commits)
[![GitHub issues](https://img.shields.io/github/issues/Jawamegamind/Weeklies.svg)](https://github.com/Jawamegamind/Weeklies/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/Jawamegamind/Weeklies.svg)](https://github.com/Jawamegamind/Weeklies/pulls)
[![Repo Size](https://img.shields.io/github/repo-size/Jawamegamind/Weeklies.svg)](https://github.com/Jawamegamind/Weeklies)
[![Contributors](https://img.shields.io/github/contributors/Jawamegamind/Weeklies.svg)](https://github.com/Jawamegamind/Weeklies/graphs/contributors)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-46a2f1?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![DOI](https://zenodo.org/badge/1042386944.svg)](https://doi.org/10.5281/zenodo.17547176)
---

## 🧠 Project Overview

**Weeklies** is a **full-stack Flask web application** developed as part of *CSC 510* : Software Engineering (Fall 2025, NC State University)*.  
It models a modern food-delivery system where users can register, browse restaurants and menus, tag preferences, and schedule future meal orders via an integrated calendar.  
The project demonstrates **modular backend design**, **frontend interaction**, **LLM-assisted personalization**, and **continuous documentation & testing pipelines**.

---

## 🎬 Videos
👉 [Click here to watch the demo video for Project 2 on YouTube](https://youtu.be/CKCTOMVMst8)  
👉 [Click here to watch the highlight reel for Project 3 on YouTube](https://youtu.be/CKCTOMVMst8)  
👉 [Click here to watch the walkthrough for Project 3 on YouTube](https://youtu.be/CKCTOMVMst8)
---

## ⚙️ Tech Stack

| Layer | Technologies | Key Focus |
|-------|---------------|-----------|
| **Frontend** | HTML, CSS, JavaScript (templated views) | Dynamic forms, order interaction, user calendar |
| **Backend** | Python 3.11+, Flask 2.x | RESTful routes, modular blueprints, DB logic |
| **Database** | SQLite / Flask-SQLAlchemy | Lightweight persistence for menus, users, orders |
| **Automation** | GitHub Actions, pdoc, pytest, ruff, black | CI/CD, linting, testing, documentation |
| **Intelligent Module** | OpenAI / LLM API | Personalized recommendations & reasoning |
| **PDF Service** | ReportLab / FPDF | Automated PDF receipt generation |

---

## 🧩 Core Features

- 👤 **User registration & authentication**
- 🍱 **Menu and restaurant search** with allergen + cuisine tagging
- 🧭 **User preference tagging** and filtering
- 📅 **Calendar-based scheduling** (order-on-selected-date logic)
- 🧾 **Dynamic PDF receipt generation**
- 🤖 **LLM integration** for context-aware meal suggestions
- 🧪 **Automated test suite** with `pytest`
- 🧰 **CI/CD workflows** for tests, linting, and documentation deployment

---

## 🧱 Architecture

SE25Fall/   
├── proj2/  
│   ├── Flask_app.py       
│   ├── templates/  
│   ├── static/  
│   ├── pdf_receipt.py  
│   ├── sqlQueries.py   
│   ├── tests/  
│   ├── llm_toolkit.py      
│   ├── menu_generation.py       
│   ├── requirements.txt    
│   ├── CSC510_DB.db    
│   └── orders_db_seed.txt  
├── .github/    
│   └── workflows/  
│           ├── ci.yml  
│           └── docs.yml    
├── INSTALLATION.md   
├── LICENSE   
├── CODE_OF_CONDUCT.md     
├── README.md   
├── scripts/       
├── pytest.ini  
├── pdoc.toml   
└── coverage.xml    

---

## 🧪 Continuous Integration

Every push or pull request to the `main` branch triggers:
1. **CI tests** via `pytest` and `coverage`  
2. **Documentation build & deployment** to GitHub Pages (`gh-pages` branch)  
3. **Static analysis** via `ruff` and `black` 

You can view live status from the badges above.

---

## 📚 Documentation

Auto-generated API documentation is available through **pdoc** and deployed automatically.  
You can view it online (via GitHub Pages) or build it locally:

🔗 **Live Docs:** [Food Delivery Documentation](https://taylorbrown96.github.io/SE25Fall/)  
🧰 **Local Build:** See [INSTALLATION.md](./INSTALLATION.md#7-build-documentation-locally)

---

## 🚀 Installation & Usage

Setup, environment creation, and execution instructions have been moved to a dedicated guide:  
➡️ **[See Installation Guide →](./INSTALLATION.md)**

---

##  👥 Team & Contributors
Project developed collaboratively as part of **CSC 510 — Software Engineering (Fall 2025, NC State University)**.

| Member | GitHub Handle | Key Contributions |
|---------|----------------|-------------------|
| **Taylor J. Brown** | [@TaylorBrown96](https://github.com/TaylorBrown96) | Led user authentication and preference management. Implemented menu tagging (allergens, cuisine types) and PDF receipt generation. Integrated JS calendar template for scheduling. Contributed to backend expansion and system testing. |
| **Kunal Jindal** | [@devkunal2002](https://github.com/devkunal2002) | Designed and automated documentation pipeline using `pdoc`. Authored Installation Guide and main README. Set up CI/CD workflows, repository structure, and code quality badging. Contributed to backend testing and verification. |
| **Ashritha Bugada** | — | Developed restaurant search, menu browsing, and ordering flow. Designed dynamic menu templates and integrated frontend-backend routes for order placement. Assisted with usability testing and validation. |
| **Daniel Dong** | — | Implemented backend for calendar scheduling and integrated LLM module for personalized recommendations. Supported expansion of core Flask app and contributed to end-to-end feature debugging. |

---

## 🤝 Contributing
We welcome contributions from everyone.  
Please make sure to review our [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

---

## 📜 License
Distributed under the MIT License.  
See [LICENSE](./LICENSE) for more information.

---

> “Build software that’s clean, testable, and transparent not just functional.”

