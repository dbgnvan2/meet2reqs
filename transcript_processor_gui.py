#!/usr/bin/env python3
"""
Meeting Transcript Processor - GUI Application
Tkinter-based interface for the meeting transcript processing pipeline.
"""

import logging
import os
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from dotenv import load_dotenv

load_dotenv()

import config
from transcript_utils import setup_logging


class GuiLogHandler(logging.Handler):
    """Logging handler that writes to a Tkinter text widget."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.after(0, self._append, msg)

    def _append(self, msg):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, msg + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)


class TranscriptProcessorApp:
    """Main GUI application for meeting transcript processing."""

    def __init__(self, root):
        self.root = root
        self.root.title("Meeting Transcript Processor")
        self.root.geometry("900x700")

        self.selected_file = None
        self.logger = None
        self.running = False

        self._build_ui()

    def _build_ui(self):
        # Title
        title = ttk.Label(
            self.root,
            text="Meeting Transcript Processor",
            font=("Helvetica", 16, "bold"),
        )
        title.pack(pady=(10, 5))

        subtitle = ttk.Label(
            self.root,
            text="Extract requirements, decisions, and action items from meeting transcripts",
        )
        subtitle.pack(pady=(0, 10))

        # File selection frame
        file_frame = ttk.LabelFrame(self.root, text="Source File", padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)

        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_btn = ttk.Button(file_frame, text="Browse...", command=self._browse_file)
        browse_btn.pack(side=tk.RIGHT)

        # Model selection frame
        model_frame = ttk.LabelFrame(self.root, text="Models", padding=10)
        model_frame.pack(fill=tk.X, padx=10, pady=5)

        models = config.settings.get_all_model_names()

        for i, (role, default) in enumerate([
            ("Cleaning", config.settings.CLEANING_MODEL),
            ("Extraction", config.settings.EXTRACTION_MODEL),
            ("Enrichment", config.settings.ENRICHMENT_MODEL),
            ("Validation", config.settings.VALIDATION_MODEL),
        ]):
            ttk.Label(model_frame, text=f"{role}:").grid(row=i, column=0, sticky=tk.W, padx=(0, 5))
            combo = ttk.Combobox(model_frame, values=models, width=40)
            combo.set(default)
            combo.grid(row=i, column=1, sticky=tk.W, pady=2)
            setattr(self, f"model_{role.lower()}", combo)

        # Action buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        self.run_btn = ttk.Button(btn_frame, text="Run Full Pipeline", command=self._run_pipeline)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Progress
        self.progress = ttk.Progressbar(self.root, mode="determinate", maximum=5)
        self.progress.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = ttk.Label(self.root, text="Ready")
        self.status_label.pack(padx=10)

        # Log output
        log_frame = ttk.LabelFrame(self.root, text="Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _browse_file(self):
        source_dir = str(config.SOURCE_DIR) if config.SOURCE_DIR.exists() else "."
        filepath = filedialog.askopenfilename(
            initialdir=source_dir,
            title="Select Meeting Transcript",
            filetypes=[("Text files", "*.txt *.md"), ("All files", "*.*")],
        )
        if filepath:
            self.selected_file = Path(filepath)
            self.file_label.config(text=self.selected_file.name)

    def _set_status(self, text, step=None):
        self.status_label.config(text=text)
        if step is not None:
            self.progress["value"] = step
        self.root.update_idletasks()

    def _log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _run_pipeline(self):
        if not self.selected_file:
            messagebox.showwarning("No File", "Please select a transcript file first.")
            return

        if not os.environ.get("ANTHROPIC_API_KEY"):
            messagebox.showerror("API Key Missing", "Set ANTHROPIC_API_KEY in .env or environment.")
            return

        self.running = True
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress["value"] = 0

        # Apply model selections
        for role in ["cleaning", "extraction", "enrichment", "validation"]:
            combo = getattr(self, f"model_{role}")
            config.settings.set_model(role, combo.get())

        thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        thread.start()

    def _stop(self):
        self.running = False
        self._set_status("Stopping...")

    def _pipeline_worker(self):
        try:
            logger = setup_logging("gui_pipeline")
            gui_handler = GuiLogHandler(self.log_text)
            gui_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logger.addHandler(gui_handler)

            raw_filename = self.selected_file.name

            # If file is not in source dir, copy it there
            source_path = config.SOURCE_DIR / raw_filename
            if not source_path.exists():
                config.SOURCE_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(self.selected_file), str(source_path))
                self._log(f"Copied to source: {source_path}")

            # Step 1: Clean
            self.root.after(0, self._set_status, "Step 1/5: Cleaning transcript...", 0)
            from formatting_pipeline import clean_transcript
            result = clean_transcript(raw_filename, logger=logger)
            base_name = result["base_name"]
            if not self.running:
                return

            # Step 2: Extract
            self.root.after(0, self._set_status, "Step 2/5: Extracting categories...", 1)
            from extraction_pipeline import extract_all
            extraction = extract_all(result["cleaned_text"], base_name, logger=logger)
            if not self.running:
                return

            # Step 3: Enrich
            self.root.after(0, self._set_status, "Step 3/5: Enriching requirements...", 2)
            enriched = []
            requirements = extraction.get("requirements", [])
            if requirements:
                from enrichment_pipeline import enrich_requirements
                enriched = enrich_requirements(requirements, base_name, logger=logger)
            if not self.running:
                return

            # Step 4: Validate
            self.root.after(0, self._set_status, "Step 4/5: Validating...", 3)
            from validation_pipeline import validate_extraction
            report = validate_extraction(
                extraction, result["cleaned_text"], base_name,
                enriched_requirements=enriched, logger=logger,
            )
            if not self.running:
                return

            # Step 5: Generate Reports
            self.root.after(0, self._set_status, "Step 5/5: Generating reports...", 4)
            from html_generator import generate_markdown_report, generate_html_report, generate_pdf_report
            generate_markdown_report(extraction, enriched, base_name, report, logger)
            generate_html_report(extraction, enriched, base_name, report, logger)
            generate_pdf_report(extraction, enriched, base_name, report, logger)

            score = report.get("overall_score", 0)
            self.root.after(0, self._set_status, f"Complete! Score: {score:.0%}", 5)
            self.root.after(0, lambda: messagebox.showinfo(
                "Complete",
                f"Processing complete!\n\n"
                f"Validation score: {score:.0%}\n"
                f"Output: {config.PROJECTS_DIR / base_name}",
            ))

        except Exception as e:
            self._log(f"ERROR: {e}")
            self.root.after(0, self._set_status, f"Error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

        finally:
            self.running = False
            self.root.after(0, lambda: self.run_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))


def main():
    root = tk.Tk()
    app = TranscriptProcessorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
