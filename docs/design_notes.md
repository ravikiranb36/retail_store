# Design Decisions

## Technology Stack
- **Backend:** Django + Django REST Framework for robust API development, authentication, and ORM support.
- **Task Queue:** Dramatiq with Redis for background processing (CSV uploads, bulk updates).
- **Frontend:** Angular for a modern, responsive, and maintainable single-page application (SPA).
- **Database:** SQLite for development; easily swappable to PostgreSQL/MySQL for production.

## Key Design Choices
- **Separation of Concerns:** Clear separation between API (Django) and UI (Angular) for scalability and maintainability.
- **Authentication:** JWT-based authentication for secure, stateless API access.
- **Role-based Access:** Store Manager, Admin, and Viewer roles with permissions enforced at the API level.
- **Bulk Operations:** CSV upload and background processing for efficient bulk updates, using Dramatiq workers.
- **Pagination:** All list endpoints are paginated to support large datasets and efficient frontend rendering.
- **Extensible Models:** Product and Store models are designed to be easily extensible for future requirements (e.g., more product/store fields).
- **Internationalization:** Currency and date formatting are handled on the frontend, with user-selectable currency and local time display.
- **Error Handling:** Consistent error responses and user feedback for all API and UI operations.

# Non-Functional Requirements & How They Are Addressed

## Scalability
- **API and UI Separation:** Allows independent scaling of backend and frontend.
- **Task Queue:** Dramatiq with Redis enables horizontal scaling for background jobs (e.g., CSV processing).
- **Pagination:** Ensures API and UI can handle large datasets efficiently.

## Performance
- **Async Processing:** CSV uploads and bulk updates are processed asynchronously to avoid blocking user requests.
- **Efficient Queries:** Use of Django ORM optimizations and indexed fields for search and filtering.

## Security
- **JWT Authentication:** Secure, stateless authentication for all API endpoints.
- **Role-based Permissions:** Only authorized users can perform sensitive actions (e.g., upload, edit, delete).
- **Input Validation:** All inputs are validated both on the backend (serializers) and frontend (forms).

## Reliability & Availability
- **Background Tasks:** Long-running operations are offloaded to Dramatiq workers, improving API reliability.
- **Error Handling:** Graceful error handling and user feedback for all operations.
- **Database Agnostic:** Can switch to a more robust DB (e.g., PostgreSQL) for production.

## Maintainability
- **Modular Codebase:** Clear separation of concerns, modular Angular components, and Django apps.
- **Documentation:** Inline code comments, docstrings, README, and architecture diagrams.

## Internationalization
- **Currency/Time:** UI supports INR, USD, EUR; dates shown in user's local time.

# Assumptions
- **User Roles:** There are three roles: Store Manager (full access to their store's data), Admin (manage stores), and Viewer (view-only access).
- **CSV Format:** The CSV for upload contains Store ID, SKU, Product Name, Price, and Date.
- **Data Volume:** The system is designed to handle thousands of stores and products, with pagination and async processing for scale.
- **Authentication:** JWT is used for all API access; no anonymous modifications allowed.
- **Deployment:** SQLite is used for development; production should use PostgreSQL or MySQL.
- **Task Queue:** Redis is available for Dramatiq background processing.
- **Frontend/Backend Deployment:** Frontend and backend can be deployed independently.

# Source
- All source code and artifacts are available in this repository.
- See `docs/context_diagram.md` and `docs/solution_diagram.md` for architecture diagrams.
- See `README.md` for setup and usage instructions.

