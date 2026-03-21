## 1. Backend chat decomposition seams

- [x] 1.1 Introduce the stable backend orchestration entrypoint that shields chat endpoints from staged internal extraction
- [x] 1.2 Extract backend chat collaborators from the current monolithic modules and route them through the stable orchestration seam

## 2. Frontend chat composition boundaries

- [x] 2.1 Introduce the shared frontend stream-consumption adapter or controller used by chat surfaces
- [x] 2.2 Split the chat page into a shell plus focused rendering, input, and state collaborators
- [x] 2.3 Align embedded and standard chat surfaces on the shared orchestration and stream-consumption behavior

## 3. Verification

- [x] 3.1 Add or update targeted chat coverage for happy-path, stream, and error-path behavior across the new seams
- [x] 3.2 Validate unchanged chat behavior for users and integrations after the decomposition slices land
