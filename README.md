# 📦 Storage API

> 🚀 A FastAPI-based file storage service with **normal uploads, chunked uploads, file management, and database-backed metadata**.

A lightweight and scalable **File Storage REST API** built with **FastAPI**.
The project supports both **direct file uploads** and **chunked uploads for large files**.

---

## ✨ Features

* 📤 **Direct File Upload**
* 🧩 **Chunked File Upload**
* 🚀 Upload large files in smaller chunks
* 🔄 Initialize upload sessions using `/init`
* 🔗 Combine uploaded chunks into a final file
* 📥 Download files
* 📋 Get file information
* 📂 List stored files
* 🗑️ Delete files
* 🗄️ Store file metadata in database
* 📚 Interactive Swagger documentation
* ⚡ Fast REST API
* 🧱 Modular FastAPI project structure

---

## 🧠 How Chunked Upload Works

Large files don't always need to be uploaded in a single request.

This API divides a large file into smaller **chunks**, uploads them individually, and then combines them into the final file.

```text
                    📁 Large File
                         │
                         ▼
                  ┌──────────────┐
                  │ /files/init  │
                  └──────┬───────┘
                         │
                    Upload ID
                         │
                         ▼
              ┌─────────────────────┐
              │    Upload Chunks    │
              └──────────┬──────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
         Chunk 1      Chunk 2      Chunk N
            │            │            │
            └────────────┼────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ /files/chunk/complete│
              └──────────┬──────────┘
                         │
                         ▼
                  📦 Final File
```

### 🔄 Upload Flow

```text
1️⃣ Initialize upload
       ↓
   /files/init

2️⃣ Upload chunks
       ↓
   /files/chunk

3️⃣ Complete upload
       ↓
   /files/chunk/complete

4️⃣ Chunks are combined
       ↓
   Final file created
```

This approach is useful for handling **large files** and improving upload reliability.

---

## 🔗 API Endpoints

### 📁 File Management

|  Method  | Endpoint               | Description            |
| :------: | ---------------------- | ---------------------- |
|  `POST`  | `/files/upload`        | Upload a complete file |
|   `GET`  | `/files`               | Get all stored files   |
|   `GET`  | `/files/{id}`          | Get file information   |
|   `GET`  | `/files/download/{id}` | Download a file        |
| `DELETE` | `/files/{id}`          | Delete a file          |

### 🧩 Chunked Upload

| Method | Endpoint                | Description                        |
| :----: | ----------------------- | ---------------------------------- |
| `POST` | `/files/init`           | Initialize a chunked upload        |
| `POST` | `/files/chunk`          | Upload an individual chunk         |
| `POST` | `/files/chunk/complete` | Combine chunks and complete upload |

---

## 🛠️ Tech Stack

| Technology                 | Purpose                    |
| -------------------------- | -------------------------- |
| 🐍 **Python**              | Programming language       |
| ⚡ **FastAPI**              | REST API framework         |
| 🗄️ **SQLAlchemy**         | ORM / Database interaction |
| 🐘 **PostgreSQL / SQLite** | Database                   |
| 🚀 **Uvicorn**             | ASGI server                |
| 📦 **Pydantic**            | Data validation            |

---

## 📂 Project Structure

```text
storage-api/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── core/
│   │   └── ...
│   │
│   ├── db/
│   │   └── ...
│   │
│   ├── model/
│   │   └── ...
│   │
│   └── routers/
│       └── ...
│
├── storage/
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/amit-rajpoot/storage-api.git
```

### 2. Enter the project

```bash
cd storage-api
```

### 3. Create virtual environment

```bash
python3 -m venv .venv
```

### 4. Activate virtual environment

```bash
source .venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Run the API

Start the development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

---

## 📚 API Documentation

FastAPI automatically provides interactive API documentation.

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### ReDoc

```text
http://127.0.0.1:8000/redoc
```

You can use **Swagger UI** to upload files, test endpoints, and inspect API responses directly from your browser.

---

## 📤 Direct Upload

For smaller files, you can directly upload the complete file:

```text
Client
  │
  │ POST /files/upload
  ▼
FastAPI
  │
  ▼
Storage
  │
  ▼
Database Metadata
```

---

## 🧩 Chunked Upload

For large files:

```text
Client
  │
  ├── /files/init
  │       ↓
  │    Upload ID
  │
  ├── /files/chunk
  │       ↓
  │    Chunk 1
  │
  ├── /files/chunk
  │       ↓
  │    Chunk 2
  │
  ├── /files/chunk
  │       ↓
  │    Chunk N
  │
  └── /files/chunk/complete
          ↓
      Final File
```
