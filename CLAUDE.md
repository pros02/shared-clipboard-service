\# CLAUDE.md



\## Project Overview



Shared Clipboard Service is a cross-platform desktop application for

sharing text, images, and files between Windows 11 and Ubuntu 26.04

through a NAS SMB shared folder.



\## Development Priorities



1\. Stability

2\. Cross-platform compatibility

3\. Simple installation

4\. Maintainable architecture

5\. Future extensibility



\## Architecture Rules



\- Separate GUI, application logic, clipboard access, and storage logic.

\- Do not put business logic directly in GUI classes.

\- Abstract the storage backend.

\- Initial storage uses a NAS shared directory.

\- Design so SQLite or REST API storage can be added later.

\- Avoid OS-specific code outside platform adapter modules.

\- Use type hints throughout.

\- Add logging and meaningful error handling.

\- Do not store credentials in the repository.



\## Initial Scope



\- Select NAS shared folder

\- Send and receive text

\- Send and receive clipboard images

\- Send and receive files

\- Manual receive

\- Optional automatic receive

\- Recent history

\- Ignore items created by the same client

\- Atomic writes to avoid reading incomplete files



\## Out of Scope



\- AKM integration

\- HMS integration

\- OCR

\- AI analysis

\- Cloud synchronization

\- User authentication

\- Internet access



\## Supported Platforms



\- Windows 11

\- Ubuntu 26.04 LTS



\## Development Workflow



Before making large changes:



1\. Read the requirements under `docs/requirements/`.

2\. Propose an implementation plan.

3\. Identify platform-specific risks.

4\. Implement in small testable steps.

5\. Update README and documentation when behavior changes.



\## Testing



\- Add unit tests for storage and metadata handling.

\- Keep clipboard platform adapters mockable.

\- Do not assume the NAS is always connected.

\- Test interrupted writes and malformed metadata.

