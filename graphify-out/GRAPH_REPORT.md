# Graph Report - .  (2026-08-04)

## Corpus Check
- Large corpus: 440 files · ~658,378 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 364 nodes · 774 edges · 22 communities (19 shown, 3 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Authentication and Sessions
- Vision Processing Pipeline
- Alternate Vision Runtime
- Events and Analytics
- Camera API Gateway
- Roster Management UI
- Desktop Edge Launcher
- Class Schedule UI
- Application Configuration
- Qt Desktop Shell
- Analytics UI Client
- Dashboard UI Client

## God Nodes (most connected - your core abstractions)
1. `SessionData` - 24 edges
2. `handle_register()` - 15 edges
3. `read_json_safe()` - 15 edges
4. `process_frame()` - 15 edges
5. `process_frame()` - 15 edges
6. `handle_camera_event()` - 14 edges
7. `update_json_atomic()` - 13 edges
8. `sanitize_camera_id()` - 13 edges
9. `accounts_file()` - 13 edges
10. `KnownFaceManager` - 13 edges

## Surprising Connections (you probably didn't know these)
- `handle_manage_account()` --calls--> `accounts_file()`  [EXTRACTED]
  handlers/admin_handlers.py → utils/paths.py
- `handle_manage_account()` --calls--> `sanitize_camera_id()`  [EXTRACTED]
  handlers/admin_handlers.py → utils/paths.py
- `_handle_delete()` --calls--> `update_json_atomic()`  [EXTRACTED]
  handlers/admin_handlers.py → services/file_service.py
- `_handle_edit()` --calls--> `update_json_atomic()`  [EXTRACTED]
  handlers/admin_handlers.py → services/file_service.py
- `handle_register()` --calls--> `accounts_file()`  [EXTRACTED]
  handlers/auth_handlers.py → utils/paths.py

## Import Cycles
- None detected.

## Communities (22 total, 3 thin omitted)

### Community 0 - "Authentication and Sessions"
Cohesion: 0.07
Nodes (55): ActionHandler, check_permission(), consume_invite_code(), Any, store_invite_code(), validate_invite_code(), Connection, _conn() (+47 more)

### Community 1 - "Vision Processing Pipeline"
Cohesion: 0.05
Nodes (35): BytesIO, Request, UploadFile, allowed_file(), camera_grid(), camera_loop(), CameraCapture, CameraFrameManager (+27 more)

### Community 2 - "Alternate Vision Runtime"
Cohesion: 0.06
Nodes (30): allowed_file(), camera_grid(), camera_loop(), CameraCapture, CameraFrameManager, connect_to_server(), delete_known_face(), detect_emotion() (+22 more)

### Community 3 - "Events and Analytics"
Cohesion: 0.16
Nodes (35): datetime, handle_camera_event(), handle_init(), _parse_timestamp(), Any, WebSocket, handle_get_json_content(), handle_get_json_files() (+27 more)

### Community 4 - "Camera API Gateway"
Cohesion: 0.08
Nodes (27): HTTPAuthorizationCredentials, WebSocketClientProtocol, get_camera_stats(), get_dashboard_page(), get_ima_file(), get_static_file(), login(), BaseModel (+19 more)

### Community 5 - "Roster Management UI"
Cohesion: 0.17
Nodes (6): displayUserInfo(), mergeAndRenderData(), renderTable(), selectRow(), sortTable(), WebSocketClient

### Community 6 - "Desktop Edge Launcher"
Cohesion: 0.24
Nodes (5): is_server_running(), JSBridge, main(), Запускает процессы в фоне, Фоновый мониторинг: если gg.py выключен через интерфейс, возвращаем экран Лаунче

### Community 7 - "Class Schedule UI"
Cohesion: 0.38
Nodes (8): getRussianDayOfWeek(), loadSchedule(), populateClassSelect(), showErrorMessage(), showNoScheduleMessage(), showWeekendMessage(), updateCurrentLesson(), updateSchedule()

### Community 8 - "Application Configuration"
Cohesion: 0.36
Nodes (3): BaseSettings, Path, Settings

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SessionData` connect `Authentication and Sessions` to `Events and Analytics`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `Settings` connect `Application Configuration` to `Authentication and Sessions`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Should `Authentication and Sessions` be split into smaller, more focused modules?**
  _Cohesion score 0.0684931506849315 - nodes in this community are weakly interconnected._
- **Should `Vision Processing Pipeline` be split into smaller, more focused modules?**
  _Cohesion score 0.051643192488262914 - nodes in this community are weakly interconnected._
- **Should `Alternate Vision Runtime` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._
- **Should `Camera API Gateway` be split into smaller, more focused modules?**
  _Cohesion score 0.0766488413547237 - nodes in this community are weakly interconnected._