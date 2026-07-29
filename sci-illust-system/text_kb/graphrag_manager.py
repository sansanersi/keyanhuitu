import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime


class GraphRAGTextKBManager:
    SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json"}
    DEFAULT_INCOMING_GROUPS = ("pathways", "receptors", "gene_regulation", "figure_captions", "glossary")

    def __init__(self, base_dir=None, focus_domain="biology"):
        if base_dir:
            self.base_dir = os.path.abspath(base_dir)
        else:
            self.base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "web_app", "data", "text_kb")
            )
        self.focus_domain = self._normalize_domain(focus_domain)

    def workspace_paths(self, domain=None):
        domain_name = self._normalize_domain(domain or self.focus_domain)
        domain_root = os.path.join(self.base_dir, domain_name)
        corpus_root = os.path.join(domain_root, "corpus")
        incoming_root = os.path.join(corpus_root, "incoming")
        raw_root = os.path.join(corpus_root, "raw")
        cleaned_root = os.path.join(corpus_root, "cleaned")
        processed_root = cleaned_root
        archive_root = os.path.join(corpus_root, "archive")
        graphrag_root = os.path.join(domain_root, "graphrag")
        input_root = os.path.join(graphrag_root, "input")
        output_root = os.path.join(graphrag_root, "output")
        cache_root = os.path.join(graphrag_root, "cache")
        return {
            "domain": domain_name,
            "domain_root": domain_root,
            "corpus_root": corpus_root,
            "incoming_root": incoming_root,
            "raw_root": raw_root,
            "cleaned_root": cleaned_root,
            "processed_root": processed_root,
            "archive_root": archive_root,
            "graphrag_root": graphrag_root,
            "input_root": input_root,
            "output_root": output_root,
            "cache_root": cache_root,
            "settings_yaml": os.path.join(graphrag_root, "settings.yaml"),
            "env_file": os.path.join(graphrag_root, ".env"),
            "readme_file": os.path.join(domain_root, "README.md"),
            "manifest_file": os.path.join(corpus_root, "manifest.json"),
        }

    def ensure_workspace(self, domain=None, initialize_cli=False, force=False):
        paths = self.workspace_paths(domain)
        for key in (
            "domain_root",
            "corpus_root",
            "incoming_root",
            "raw_root",
            "cleaned_root",
            "archive_root",
            "graphrag_root",
            "input_root",
            "output_root",
            "cache_root",
        ):
            os.makedirs(paths[key], exist_ok=True)
        self._ensure_incoming_groups(paths)

        if not os.path.exists(paths["readme_file"]):
            with open(paths["readme_file"], "w", encoding="utf-8") as f:
                f.write(self._readme_text(paths["domain"]))

        self._ensure_manifest(paths)

        cli_path = self._graphrag_executable()
        init_result = {"initialized": False, "cli_available": cli_path is not None, "command": None}

        if initialize_cli and cli_path:
            if force:
                self._backup_existing_workspace_files(paths)
            command = [cli_path, "init", "--root", paths["graphrag_root"]]
            subprocess.run(command, check=True, capture_output=True, text=True, env=self._command_env(cli_path))
            init_result = {"initialized": True, "cli_available": True, "command": " ".join(command)}
        else:
            self._write_template_files(paths)

        return {**paths, **init_result}

    def stage_document(self, filepath, filename=None, domain=None, source_label="upload"):
        source_path = os.path.abspath(filepath)
        name = filename or os.path.basename(source_path)
        ext = os.path.splitext(name)[1].lower()
        if ext not in self.SUPPORTED_TEXT_EXTENSIONS:
            return {"success": False, "reason": "unsupported", "filename": name}

        paths = self.ensure_workspace(domain)
        safe_name = self._safe_filename(name)
        incoming_target = os.path.join(paths["incoming_root"], safe_name)
        raw_target = os.path.join(paths["raw_root"], safe_name)
        cleaned_target = os.path.join(paths["cleaned_root"], safe_name)
        input_target = os.path.join(paths["input_root"], safe_name)

        if not self._is_within_directory(source_path, paths["incoming_root"]) and source_path != incoming_target:
            shutil.copy2(source_path, incoming_target)
        if source_path != raw_target:
            shutil.copy2(source_path, raw_target)

        content = self._read_text_file(source_path)
        cleaned_content = self._normalize_text(content)
        with open(cleaned_target, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        with open(input_target, "w", encoding="utf-8") as f:
            f.write(cleaned_content)

        self._upsert_manifest_document(
            paths,
            {
                "filename": safe_name,
                "domain": paths["domain"],
                "source_label": source_label,
                "status": "active",
                "hash": self._content_hash(cleaned_content),
                "source_path": source_path,
                "incoming_path": incoming_target,
                "raw_path": raw_target,
                "cleaned_path": cleaned_target,
                "input_path": input_target,
                "imported_at": self._timestamp(),
            },
        )

        return {
            "success": True,
            "domain": paths["domain"],
            "filename": safe_name,
            "incoming_path": incoming_target,
            "raw_path": raw_target,
            "cleaned_path": cleaned_target,
            "input_path": input_target,
        }

    def import_documents(self, domain=None, source_dir=None, archive=True):
        paths = self.ensure_workspace(domain)
        source_root = os.path.abspath(source_dir or paths["incoming_root"])
        manifest = self._load_manifest(paths)
        known_hashes = {doc.get("hash", "") for doc in manifest["documents"] if doc.get("status") == "active"}

        imported = 0
        skipped_duplicates = 0
        skipped_unsupported = 0
        errors = []

        for root, _, files in os.walk(source_root):
            for name in files:
                if name.lower() == "readme.md":
                    skipped_unsupported += 1
                    continue
                ext = os.path.splitext(name)[1].lower()
                source_path = os.path.join(root, name)
                if ext not in self.SUPPORTED_TEXT_EXTENSIONS:
                    skipped_unsupported += 1
                    continue
                try:
                    content = self._read_text_file(source_path)
                    cleaned_content = self._normalize_text(content)
                    content_hash = self._content_hash(cleaned_content)
                    if content_hash in known_hashes:
                        skipped_duplicates += 1
                        continue
                    known_hashes.add(content_hash)
                    self.stage_document(source_path, filename=name, domain=paths["domain"], source_label="incoming")
                    imported += 1
                    if archive and os.path.abspath(source_root) == os.path.abspath(paths["incoming_root"]):
                        archive_target = os.path.join(paths["archive_root"], self._safe_filename(name))
                        shutil.move(source_path, archive_target)
                except Exception as exc:
                    errors.append({"filename": name, "error": str(exc)})

        return {
            "domain": paths["domain"],
            "source_dir": source_root,
            "imported": imported,
            "skipped_duplicates": skipped_duplicates,
            "skipped_unsupported": skipped_unsupported,
            "errors": errors,
        }

    def sync_directory(self, source_dir, domain=None):
        paths = self.ensure_workspace(domain)
        staged = 0
        skipped = 0
        for root, _, files in os.walk(source_dir):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                source_path = os.path.join(root, name)
                if ext not in self.SUPPORTED_TEXT_EXTENSIONS:
                    skipped += 1
                    continue
                result = self.stage_document(source_path, filename=name, domain=paths["domain"])
                if result["success"]:
                    staged += 1
                else:
                    skipped += 1
        return {"domain": paths["domain"], "staged": staged, "skipped": skipped}

    def status(self, domain=None):
        paths = self.ensure_workspace(domain)
        raw_docs = self._count_files(paths["raw_root"])
        cleaned_docs = self._count_files(paths["cleaned_root"])
        input_docs = self._count_files(paths["input_root"])
        output_docs = self._count_files(paths["output_root"])
        incoming_docs = self._count_files(paths["incoming_root"])
        executable = self._graphrag_executable()
        manifest = self._load_manifest(paths)
        return {
            "domain": paths["domain"],
            "base_dir": self.base_dir,
            "graphrag_cli": executable is not None,
            "graphrag_executable": executable or "",
            "workspace_root": paths["graphrag_root"],
            "settings_exists": os.path.exists(paths["settings_yaml"]),
            "env_exists": os.path.exists(paths["env_file"]),
            "manifest_entries": len(manifest["documents"]),
            "incoming_documents": incoming_docs,
            "raw_documents": raw_docs,
            "cleaned_documents": cleaned_docs,
            "input_documents": input_docs,
            "output_artifacts": output_docs,
            "index_ready": self._index_ready(paths),
        }

    def cli_available(self):
        return self._graphrag_executable() is not None

    def run_index(self, domain=None):
        paths = self.ensure_workspace(domain)
        executable = self._graphrag_executable()
        if not executable:
            return {"success": False, "available": False, "error": "graphrag cli not found"}

        command = [executable, "index", "--root", paths["graphrag_root"]]
        result = subprocess.run(command, capture_output=True, text=True, env=self._command_env(executable))
        return {
            "success": result.returncode == 0,
            "available": True,
            "command": " ".join(command),
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
            "returncode": result.returncode,
            "output_root": paths["output_root"],
        }

    def query(self, text, domain=None, method="local", response_type="Multiple Paragraphs"):
        query_text = str(text or "").strip()
        paths = self.ensure_workspace(domain)
        executable = self._graphrag_executable()

        if not query_text:
            return {"available": False, "query": "", "method": method, "answer": "", "error": "empty query"}
        if not executable:
            return {
                "available": False,
                "query": query_text,
                "method": method,
                "answer": "",
                "error": "graphrag cli not found",
            }
        if not self._index_ready(paths):
            return {
                "available": False,
                "query": query_text,
                "method": method,
                "answer": "",
                "error": "index not ready",
            }

        command = [
            executable,
            "query",
            "--method",
            method,
            "--query",
            query_text,
            "--root",
            paths["graphrag_root"],
            "--response-type",
            response_type,
        ]
        result = subprocess.run(command, capture_output=True, text=True, env=self._command_env(executable))
        answer = self._extract_query_answer(result.stdout or "") or (result.stderr or "").strip()
        return {
            "available": result.returncode == 0,
            "query": query_text,
            "method": method,
            "answer": answer,
            "error": "" if result.returncode == 0 else answer,
            "command": " ".join(command),
            "returncode": result.returncode,
        }

    def reset_workspace(self, domain=None):
        paths = self.ensure_workspace(domain)
        for key in ("raw_root", "cleaned_root", "input_root", "output_root", "cache_root"):
            self._clear_directory(paths[key])

        logs_root = os.path.join(paths["graphrag_root"], "logs")
        if os.path.isdir(logs_root):
            self._clear_directory(logs_root)

        manifest = self._load_manifest(paths)
        manifest["documents"] = []
        self._save_manifest(paths, manifest)
        return {"success": True, "domain": paths["domain"]}

    def _write_template_files(self, paths):
        if not os.path.exists(paths["settings_yaml"]):
            with open(paths["settings_yaml"], "w", encoding="utf-8") as f:
                f.write(self._settings_template())
        if not os.path.exists(paths["env_file"]):
            with open(paths["env_file"], "w", encoding="utf-8") as f:
                f.write("GRAPHRAG_API_KEY=\n")

    def _ensure_manifest(self, paths):
        if not os.path.exists(paths["manifest_file"]):
            manifest = {
                "domain": paths["domain"],
                "updated_at": self._timestamp(),
                "documents": [],
            }
            with open(paths["manifest_file"], "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

    def _ensure_incoming_groups(self, paths):
        for name in self.DEFAULT_INCOMING_GROUPS:
            os.makedirs(os.path.join(paths["incoming_root"], name), exist_ok=True)

    def _load_manifest(self, paths):
        self._ensure_manifest(paths)
        with open(paths["manifest_file"], "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_manifest(self, paths, manifest):
        manifest["updated_at"] = self._timestamp()
        with open(paths["manifest_file"], "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    def _upsert_manifest_document(self, paths, document):
        manifest = self._load_manifest(paths)
        docs = [doc for doc in manifest["documents"] if doc.get("hash") != document.get("hash")]
        docs.append(document)
        manifest["documents"] = sorted(docs, key=lambda item: item.get("filename", ""))
        self._save_manifest(paths, manifest)

    def _normalize_domain(self, value):
        text = str(value or "").strip().lower()
        if not text:
            return "biology"
        return re.sub(r"[^a-z0-9_\-]+", "_", text).strip("_") or "biology"

    def _safe_filename(self, filename):
        name, ext = os.path.splitext(filename)
        safe_name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._\-]+", "_", name).strip("._") or "document"
        return safe_name + ext.lower()

    def _read_text_file(self, path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _normalize_text(self, text):
        value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        value = re.sub(r"\n{3,}", "\n\n", value)
        value = re.sub(r"[ \t]+\n", "\n", value)
        return value.strip() + ("\n" if value.strip() else "")

    def _content_hash(self, text):
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    def _count_files(self, root):
        if not os.path.isdir(root):
            return 0
        count = 0
        for _, _, files in os.walk(root):
            count += len(files)
        return count

    def _is_within_directory(self, path, root):
        try:
            return os.path.commonpath([os.path.abspath(path), os.path.abspath(root)]) == os.path.abspath(root)
        except ValueError:
            return False

    def _clear_directory(self, root):
        if not os.path.isdir(root):
            return
        for name in os.listdir(root):
            target = os.path.join(root, name)
            try:
                if os.path.isdir(target):
                    shutil.rmtree(target)
                else:
                    os.remove(target)
            except PermissionError:
                continue

    def _graphrag_executable(self):
        direct = shutil.which("graphrag")
        if direct:
            return direct

        candidates = [
            os.path.join(os.path.dirname(sys.executable), "Scripts", "graphrag.exe"),
            os.path.join(os.environ.get("APPDATA", ""), "Python", "Python312", "Scripts", "graphrag.exe"),
            os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Python", "Python312", "Scripts", "graphrag.exe"),
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    def _command_env(self, executable=None):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        cli_path = executable or self._graphrag_executable()
        if cli_path:
            cli_dir = os.path.dirname(cli_path)
            env["PATH"] = cli_dir + os.pathsep + env.get("PATH", "")
        return env

    def _index_ready(self, paths):
        required = (
            "create_final_entities.parquet",
            "create_final_relationships.parquet",
            "create_final_text_units.parquet",
        )
        return all(os.path.exists(os.path.join(paths["output_root"], name)) for name in required)

    def _backup_existing_workspace_files(self, paths):
        for source, backup in (
            (paths["settings_yaml"], os.path.join(paths["graphrag_root"], "settings.template.bak")),
            (paths["env_file"], os.path.join(paths["graphrag_root"], ".env.template.bak")),
        ):
            if os.path.exists(source) and not os.path.exists(backup):
                shutil.copy2(source, backup)

    def _extract_query_answer(self, stdout):
        text = (stdout or "").strip()
        if not text:
            return ""
        marker = "SUCCESS: Local Search Response:"
        if marker in text:
            return text.split(marker, 1)[1].strip()
        marker = "SUCCESS: Global Search Response:"
        if marker in text:
            return text.split(marker, 1)[1].strip()
        return text

    def _timestamp(self):
        return datetime.now().isoformat(timespec="seconds")

    def _settings_template(self):
        return (
            "# GraphRAG workspace template\n"
            "# 如果本机已经安装 graphrag，可在此目录运行:\n"
            "# graphrag init --root .\n"
            "# graphrag index --root .\n"
            "models:\n"
            "  default_chat_model:\n"
            "    type: openai_chat\n"
            "    api_base: ${GRAPHRAG_API_BASE}\n"
            "    model: ${GRAPHRAG_MODEL}\n"
            "    api_key: ${GRAPHRAG_API_KEY}\n"
        )

    def _readme_text(self, domain):
        return (
            "# Text Knowledge Base\n\n"
            "领域: " + domain + "\n\n"
            "- `corpus/incoming`: 待导入语料\n"
            "- `corpus/raw`: 原始文本语料\n"
            "- `corpus/cleaned`: 清洗后的语料\n"
            "- `corpus/archive`: 已归档导入文件\n"
            "- `corpus/manifest.json`: 语料登记清单\n"
            "- `graphrag/input`: GraphRAG 输入目录\n"
            "- `graphrag/output`: GraphRAG 索引输出目录\n"
            "- `graphrag/settings.yaml`: GraphRAG 配置文件\n"
        )
