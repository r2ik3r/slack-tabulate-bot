***

## Project Prompt: Intelligent Slack Bot - The Table Beautifier

### 1. High-Level Goal

Create a production-ready, distributable Slack bot named "Table Beautifier." The bot's primary function is to intelligently detect, parse, and format various types of tabular data posted in Slack messages, presenting the data back to the user in a clean, usable format.

The final application must be robust, easy for others to deploy, and ready for submission to the official Slack App Directory.

### 2. Core Features & Requirements

The bot's functionality will be defined by the following requirements:

#### 2.1. Input Triggers & Output Formats
The bot must respond to three distinct user actions:
1.  **Automatic Detection (Direct Paste):** When a user pastes tabular data into a channel, DM, or thread where the bot is present, the bot will automatically parse it and post a **scrollable CSV snippet**.
2.  **Slash Command (`/csv`):** When a user invokes the `/csv` command with tabular data, the bot will post a **scrollable CSV snippet**.
3.  **App Mention (`@Table Beautifier`):** When a user mentions the bot with tabular data, it will post a formatted **plain-text table** (using monospaced text and borders).

#### 2.2. Advanced Parsing Capabilities
The core parsing engine must be able to handle a wide variety of real-world data formats and edge cases:
-   **Multiple Delimiters:** It must correctly parse data separated by commas (CSV), tabs (TSV), semicolons (`;`), and pipes (`|`).
-   **Complex Tab/Space Data:** It must handle data where columns are separated by a mix of tabs and multiple spaces.
-   **Messy & Ragged Data:** It must successfully parse tables even if some rows have fewer columns or empty cells (e.g., `value1,,value3`).
-   **Quoted Data:** It must correctly handle cells that contain the delimiter within quotes (e.g., `"Laptop, Pro",1200`).
-   **Thousand Separators:** It must correctly interpret numbers that use commas as thousand separators (e.g., `1,250.50`) as numeric values, provided the primary delimiter is not also a comma.
-   **Diverse Data Types:** The parser should handle various data types, including strings, integers, floats, dates, Unicode characters (e.g., `नई दिल्ली`), and special symbols (e.g., `©`, `α`).

#### 2.3. Context and Multi-Table Handling
The bot must be intelligent about the text surrounding the data:
-   **Context Preservation:** The bot must detect and preserve any prose (context) that appears before or after a table block.
-   **Multiple Tables:** If a single message contains multiple distinct table blocks (separated by blank lines), the bot must identify each one and post a separate, corresponding reply for each table.
-   **Correct Output Order:** For each table found, the output message must be ordered as follows:
    1.  The context that immediately preceded the table.
    2.  The row and column count of the table (e.g., `📊 Rows: 6 • Columns: 7`).
    3.  The CSV snippet or formatted text table.
-   **Final Context:** Any context appearing after the very last table in a message must be posted as a final, separate message.

#### 2.4. Data Transformation
-   **Automatic Indexing:** If a parsed table does not already have an index column (e.g., a column named '#', 'Row', 'ID', etc.), the bot must automatically add a new "Row" column to the beginning of the output, numbered sequentially from 1.
-   **No Header Detection:** If a table is pasted without a header row, the bot must detect this and assign generic column names (e.g., `Column_1`, `Column_2`, etc.).

### 3. Technical & Architectural Requirements

-   **Language & Libraries:** The project must be written in Python, using `pandas` for data manipulation, `tabulate` for text table formatting, and `slack-bolt` for Slack API interaction.
-   **Dependency Management:** The project must use **Poetry** for dependency and environment management.
-   **Dual Run Modes:**
    1.  **Production Mode (`app.py`):** Must run as an HTTP server (e.g., with Gunicorn) and support the full OAuth 2.0 flow for multi-workspace installation. This is the version for deployment and submission to the App Directory.
    2.  **Development Mode (`run_dev.py`):** Must use Slack's **Socket Mode** for easy local development and testing without requiring a public URL or tunneling.
-   **Code Structure:** The code must be well-organized, separating the core bot logic (`handlers.py`) from the server setup (`app.py`, `run_dev.py`) and the parsing engine (`table_formatter.py`).

### 4. Deliverables

The final project should be a complete, open-source repository containing:
1.  All Python source code (`app.py`, `run_dev.py`, `handlers.py`, `table_formatter.py`).
2.  A `pyproject.toml` file defining all project dependencies and metadata.
3.  A `LICENSE` file (using the MIT License).
4.  A comprehensive `README.md` file explaining the project, its features, and detailed setup instructions for both developers and for public distribution.
5.  All necessary configuration files for deployment (e.g., `.gitignore`, `.env.example`).