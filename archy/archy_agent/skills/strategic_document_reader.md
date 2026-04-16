### **Agent Skill: StrategicDocumentReader**

**Objective:** To ingest large technical documents (PDFs, Manuals, Datasheets) efficiently while preventing context window saturation and "lost in the middle" phenomena.

**Execution Logic:**
1.  **Stat Analysis:** Run `ls -lh` to determine the file size.
2.  **Triage:**
    * **Tier 1 (Small) < 100KB:** Execute a full read immediately.
    * **Tier 2 (Large) > 100KB:** * **Phase A (Scan):** Use the reading tool to extract only the first 3–5 pages. 
        * **Phase B (Index):** Locate the Table of Contents or "Register Map" sections.
        * **Phase C (Extract):** Target specific page ranges or sections based on the current design step (e.g., "Pinout Definitions" for Step 1, or "Electrical Characteristics" for Step 2).

