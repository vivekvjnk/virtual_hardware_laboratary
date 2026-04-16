# Module wise useage for workspace manager

## 1. Bootstrap pipeline

### Consumed resources/information 
- Set of documents and images
- Module name 
- ASIC name

### Responsibility
- Prepare basic project and module directory structure
- Index and preprocess all available resources 
    1. Reference schematic image 
        - Gray scale conversion + contrast increase
        - Image segment preparation
    2. System boundary document
    3. Module boundary document
    (Optional documents)
    4. datasheet of main ASIC
    5. Eval design document of main ASIC
- Convert all pdf files(if any) to markdown files, collect all images from the pdf files to a dedicated folder(lets name the folder raw_images/)
- Prepare dictionary of available documents with document name as key, path as value

### Expected artefacts in workspace 
1. Dedicated module directory, with module name as the directory name
2. Resources directory inside module directory
    - All resources should be structurally organized inside this directory
    - reference_schematic_image directory with image segments subdirectory should be present

- Sample workspace after execution of bootstrap pipeline
vhl_workspace/bms-project/bms-monitor-module
└── resources
    ├── bms-monitor-module-boundary.md
    ├── bq79616-datasheet.md
    ├── BQ79616-eval-board.md
    ├── schematic_images
    │   ├── bms-monitor-module_preprocessed.png
    │   ├── segment_0.png
    │   ├── segment_1.png
    │   ├── segment_2.png
    │   ├── segment_3.png
    │   └── segments_overview_with_bboxes.png
    └── system-boundary.md
### Workspace manager dependency 
- Initial project/module setup
- Creat project/module directory if not present

## 2. Archy 

### Consumed resources/information
- Project root path
- Module name
- Everything from resources/ directory

### Responsibility 
- Generate Shared Circuit Understanding Document(SCUD)

### Expected artefacts in workspace
- scud document in module root

- Sample workspace after execution of Archy
vhl_workspace/bms-project/bms-monitor-module
├── resources
│   ├── bms-monitor-module-boundary.md
|   ├── bq79616-datasheet.md
|   ├── BQ79616-eval-board.md
|   ├── schematic_images
|   │   ├── bms-monitor-module_preprocessed.png
|   │   ├── segment_0.png
|   │   ├── segment_1.png
|   │   ├── segment_2.png
|   │   ├── segment_3.png
|   │   └── segments_overview_with_bboxes.png
|   └── system-boundary.md
└── bms-monitor-module.scud
### Workspace manager dependency 
- Agent workspace: Module directory

## 3. Librarian
### Consumed resources/information
- SCUD document

### Responsibility 
- Import necessary niche components 

### Expected artefacts in workspace
- Imported components inside <project_root>/lib/imports/ directory

- Sample workspace after execution of librarian 
vhl_workspace/bms-project
├──bms-monitor-module
|   ├── resources
|   │   ├── bms-monitor-module-boundary.md
|   |   ├── bq79616-datasheet.md
|   |   ├── BQ79616-eval-board.md
|   |   ├── schematic_images
│   |   │   ├── bms-monitor-module_preprocessed.png
│   |   │   ├── segment_0.png
│   |   │   ├── segment_1.png
│   |   │   ├── segment_2.png
│   |   │   ├── segment_3.png
│   |   │   └── segments_overview_with_bboxes.png
|   |   └── system-boundary.md
|   └── bms-monitor-module.scud
└── lib/imports
    ├── component_1.tsx
    ├── component_2.tsx
    └── ...

### Workspace manager dependency 
- Agent need access to scud document. Agent workspace is module directory

## 4. ANA
### Consumed resources/information
- SCUD 
- Everything from resources/ directory

### Responsibility
- Create module schematic code 
- Evaluate and error correct schematic code
- Update schematic code

### Expected artefacts in workspace
- schematic code in tsx format
vhl_workspace/bms-project
├──bms-monitor-module
|   ├── resources/
|   ├── bms-monitor-module.scud
|   ├── Stable
|   |    ├── eval_results
|   |    ├── bms-monitor-module.tsx
|   |    ├── lib/ (symbolic link)
|   |    ├── bms-monitor-module.scud (symbolic link)
|   |    └── resources/ (symbolic link)
|   ├── Iterations
|   |   ├── <iter id 1>
|   |   |   ├── bms-monitor-module.tsx
|   |   |   ├── lib/ (symbolic link)
|   |   |   ├── bms-monitor-module.scud (symbolic link)
|   |   |   └── resources/ (symbolic link)
|   |   ├── <iter id 2>
|   |   |   ├── bms-monitor-module.tsx
|   |   |   ├── lib/ (symbolic link)
|   |   |   ├── bms-monitor-module.scud (symbolic link)
|   |   |   └── resources/ (symbolic link)
|   |   ├── ...
|   |   └── <iter id 5>
|   |       ├── bms-monitor-module.tsx
|   |       ├── lib/ (symbolic link)
|   |       ├── bms-monitor-module.scud (symbolic link)
|   |       └── resources/ (symbolic link)
|   |
|   └── Archives
|       ├── <datetime-1>
|       |   └── <Content of Iterations 1>
|       ├── <datetime-2>
|       |   └── <Content of Iterations 2>
|       └── ...
|
└── lib/imports/

### Workspace manager dependency 
- Agent workspace is confinded to <iter id x> directory. Workspace manager should provide this