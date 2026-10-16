# Shared UI components

This folder contains small, typed React components styled to match King Zarry AI's existing dark/cyan interface.

Import only what a screen needs:

```tsx
import { Button, Card, SearchBar, TabbedContent } from "@/components/shared";
```

- `Header`, `Footer`, `Nav`, `Sidebar`: semantic layout primitives.
- `Button`, `Form`, `Card`: consistent controls and surfaces.
- `Carousel`, `Pagination`, `SearchBar`: navigation and content helpers.
- `Modal`, `Dropdown`, `Accordion`, `TabbedContent`: interactive UI patterns.
- `Toast`, `LoadingSpinner`: status feedback.

These are reusable building blocks, not demo screens. Existing application-specific components remain unchanged; adopt these primitives incrementally where they fit rather than replacing working chat or connector flows wholesale.
