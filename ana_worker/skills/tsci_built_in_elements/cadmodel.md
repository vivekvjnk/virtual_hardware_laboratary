# <cadmodel />

The `<cadmodel />` element is used to display a 3D model of a component, it is usually part of a [`<cadassembly />`](/elements/cadassembly) or [`<chip />`](/elements/chip).

```
export default () => (  <board>    <chip      name="U1"      footprint="soic8"      cadModel={        <cadmodel          modelUrl="https://modelcdn.tscircuit.com/jscad_models/soic8.glb"        />      }    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAAz2PMQ6DMAxF957CygQLUbeqItygI3MVklBSBRwlRqpU9e4FN3Ty%2F8%2Byv%2B1eEROBdaNeA0FVg%2BqgOgG0A%2Bpku01t2kw%2BsgJY9OyU6M%2Bi%2BBGRYvILKZHRm8vBjbY3tC6odwH7Gm3nnf0JAPs%2BBSUmopivUjIxdmkoG5%2FM6qkxOMtn3qbv3MySk5pHGI40APk7FeDDlW0ryxP1FxLsg5%2FnAAAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAAz2PMQ6DMAxF957CygQLUbeqItygI3MVklBSBRwlRqpU9e4FN3Ty%2F8%2Byv%2B1eEROBdaNeA0FVg%2BqgOgG0A%2Bpku01t2kw%2BsgJY9OyU6M%2Bi%2BBGRYvILKZHRm8vBjbY3tC6odwH7Gm3nnf0JAPs%2BBSUmopivUjIxdmkoG5%2FM6qkxOMtn3qbv3MySk5pHGI40APk7FeDDlW0ryxP1FxLsg5%2FnAAAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAAz2PMQ6DMAxF957CygQLUbeqItygI3MVklBSBRwlRqpU9e4FN3Ty%2F8%2Byv%2B1eEROBdaNeA0FVg%2BqgOgG0A%2Bpku01t2kw%2BsgJY9OyU6M%2Bi%2BBGRYvILKZHRm8vBjbY3tC6odwH7Gm3nnf0JAPs%2BBSUmopivUjIxdmkoG5%2FM6qkxOMtn3qbv3MySk5pHGI40APk7FeDDlW0ryxP1FxLsg5%2FnAAAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAAz2PMQ6DMAxF957CygQLUbeqItygI3MVklBSBRwlRqpU9e4FN3Ty%2F8%2Byv%2B1eEROBdaNeA0FVg%2BqgOgG0A%2Bpku01t2kw%2BsgJY9OyU6M%2Bi%2BBGRYvILKZHRm8vBjbY3tC6odwH7Gm3nnf0JAPs%2BBSUmopivUjIxdmkoG5%2FM6qkxOMtn3qbv3MySk5pHGI40APk7FeDDlW0ryxP1FxLsg5%2FnAAAA)

## Repositioning the Model[​](#repositioning-the-model "Direct link to Repositioning the Model")

You can use `positionOffset`, `rotationOffset`, and `zOffsetFromSurface` to reposition the model.

```
export default () => (  <board>    <chip      name="U1"      footprint="soic8"      cadModel={        <cadmodel          positionOffset={{ x: -2, y: 0, z: 0 }}          rotationOffset={{ x: 0, y: 0, z: 45 }}          modelUrl="https://modelcdn.tscircuit.com/jscad_models/soic8.glb"        />      }    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA2WQzYrCMBSF9%2FMUh64UnGZmmIGhGN9AXLmWmKQaaXtDcgW1%2BO7GWEVxE879cs%2F9swdPgWFsrfYNYzSGnGH0AUzXpIKZJZW03jqfFdCp1spi%2BV0McU3EPriOZRHJ6f8718rMydhG9gO4llGmvbIHATxFx466RV1Hy7Lvcajw%2BTPBscLXBKf04nx%2BMgRi9WZImY%2F8379XQ%2B64DI0stsw%2BVkJkok1XctQu6L3jUlMrdjHNt8qfUeRdyk2zvu8DiNsxgFv1HE7FcKbxBfVFdZxJAQAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA2WQzYrCMBSF9%2FMUh64UnGZmmIGhGN9AXLmWmKQaaXtDcgW1%2BO7GWEVxE879cs%2F9swdPgWFsrfYNYzSGnGH0AUzXpIKZJZW03jqfFdCp1spi%2BV0McU3EPriOZRHJ6f8718rMydhG9gO4llGmvbIHATxFx466RV1Hy7Lvcajw%2BTPBscLXBKf04nx%2BMgRi9WZImY%2F8379XQ%2B64DI0stsw%2BVkJkok1XctQu6L3jUlMrdjHNt8qfUeRdyk2zvu8DiNsxgFv1HE7FcKbxBfVFdZxJAQAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA2WQzYrCMBSF9%2FMUh64UnGZmmIGhGN9AXLmWmKQaaXtDcgW1%2BO7GWEVxE879cs%2F9swdPgWFsrfYNYzSGnGH0AUzXpIKZJZW03jqfFdCp1spi%2BV0McU3EPriOZRHJ6f8718rMydhG9gO4llGmvbIHATxFx466RV1Hy7Lvcajw%2BTPBscLXBKf04nx%2BMgRi9WZImY%2F8379XQ%2B64DI0stsw%2BVkJkok1XctQu6L3jUlMrdjHNt8qfUeRdyk2zvu8DiNsxgFv1HE7FcKbxBfVFdZxJAQAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA2WQzYrCMBSF9%2FMUh64UnGZmmIGhGN9AXLmWmKQaaXtDcgW1%2BO7GWEVxE879cs%2F9swdPgWFsrfYNYzSGnGH0AUzXpIKZJZW03jqfFdCp1spi%2BV0McU3EPriOZRHJ6f8718rMydhG9gO4llGmvbIHATxFx466RV1Hy7Lvcajw%2BTPBscLXBKf04nx%2BMgRi9WZImY%2F8379XQ%2B64DI0stsw%2BVkJkok1XctQu6L3jUlMrdjHNt8qfUeRdyk2zvu8DiNsxgFv1HE7FcKbxBfVFdZxJAQAA)

### Z-Offset from Surface[​](#z-offset-from-surface "Direct link to Z-Offset from Surface")

Use `zOffsetFromSurface` to control the vertical distance of the model from the PCB surface. This is useful for components that need to be positioned above or below the board surface.

```
export default () => (  <board>    <chip      name="U1"      footprint="soic8"      cadModel={        <cadmodel          zOffsetFromSurface="2mm"          modelUrl="https://modelcdn.tscircuit.com/jscad_models/soic8.glb"        />      }    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA0WPuw7CMAxFd77C6tQujWBCqOnIhhhQZ5TmQYOSJkpcCYH4d9LQghdfH8vXtnx4FxCEVGwyCGUFtIVyA9D0jgXRJpU0H7TPCmBkVtKi2xZLrZxDH%2FSItIhO8%2F3KORMnJ6ShrwXMNkzYmf0IwPOsVJR4DM5epqAYT%2BY7a1eXOfJIFwwtBkQfD4RkwsVYY%2BQ68EljzZ0l95gWXHMzknxMfTP934p8vwF455zLhix%2FVh8c9x2nCgEAAA%3D%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA0WPuw7CMAxFd77C6tQujWBCqOnIhhhQZ5TmQYOSJkpcCYH4d9LQghdfH8vXtnx4FxCEVGwyCGUFtIVyA9D0jgXRJpU0H7TPCmBkVtKi2xZLrZxDH%2FSItIhO8%2F3KORMnJ6ShrwXMNkzYmf0IwPOsVJR4DM5epqAYT%2BY7a1eXOfJIFwwtBkQfD4RkwsVYY%2BQ68EljzZ0l95gWXHMzknxMfTP934p8vwF455zLhix%2FVh8c9x2nCgEAAA%3D%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA0WPuw7CMAxFd77C6tQujWBCqOnIhhhQZ5TmQYOSJkpcCYH4d9LQghdfH8vXtnx4FxCEVGwyCGUFtIVyA9D0jgXRJpU0H7TPCmBkVtKi2xZLrZxDH%2FSItIhO8%2F3KORMnJ6ShrwXMNkzYmf0IwPOsVJR4DM5epqAYT%2BY7a1eXOfJIFwwtBkQfD4RkwsVYY%2BQ68EljzZ0l95gWXHMzknxMfTP934p8vwF455zLhix%2FVh8c9x2nCgEAAA%3D%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA0WPuw7CMAxFd77C6tQujWBCqOnIhhhQZ5TmQYOSJkpcCYH4d9LQghdfH8vXtnx4FxCEVGwyCGUFtIVyA9D0jgXRJpU0H7TPCmBkVtKi2xZLrZxDH%2FSItIhO8%2F3KORMnJ6ShrwXMNkzYmf0IwPOsVJR4DM5epqAYT%2BY7a1eXOfJIFwwtBkQfD4RkwsVYY%2BQ68EljzZ0l95gWXHMzknxMfTP934p8vwF455zLhix%2FVh8c9x2nCgEAAA%3D%3D)

## Importing local GLB models[​](#importing-local-glb-models "Direct link to Importing local GLB models")

```
import dip4ModelUrl from "./models/dip4.glb"export default () => (<board>  <chip    name="U1"    footprint="dip4"    cadModel={<cadmodel modelUrl={dip4ModelUrl} />}  /></board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&fs_map=H4sIAJsBqGcAA2WPzQqDMBCEX2XJqUIxFHoqKkjpoYee1FsgRBPbQP6IKQjiuzexCIVelmV2Z%2BfbBUnDxZyHaUYXRIzUzvoAXLrzw3KhOq9g9FYDQTnWSZlwGuZP1ZO4T4yYvw4xsrcKcMigrOBATNFb5nlFDEAxvKRLDYBhWpQEdadkTsJobXBemhDVdHjXB8Y3gHIpYrslw1YjUbn88q2AqzWZcAwr8B6bEYOO%2F9DxS0qbtm7vV1o3za2lFK0fe5hUDAYBAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&fs_map=H4sIAJsBqGcAA2WPzQqDMBCEX2XJqUIxFHoqKkjpoYee1FsgRBPbQP6IKQjiuzexCIVelmV2Z%2BfbBUnDxZyHaUYXRIzUzvoAXLrzw3KhOq9g9FYDQTnWSZlwGuZP1ZO4T4yYvw4xsrcKcMigrOBATNFb5nlFDEAxvKRLDYBhWpQEdadkTsJobXBemhDVdHjXB8Y3gHIpYrslw1YjUbn88q2AqzWZcAwr8B6bEYOO%2F9DxS0qbtm7vV1o3za2lFK0fe5hUDAYBAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&fs_map=H4sIAJsBqGcAA2WPzQqDMBCEX2XJqUIxFHoqKkjpoYee1FsgRBPbQP6IKQjiuzexCIVelmV2Z%2BfbBUnDxZyHaUYXRIzUzvoAXLrzw3KhOq9g9FYDQTnWSZlwGuZP1ZO4T4yYvw4xsrcKcMigrOBATNFb5nlFDEAxvKRLDYBhWpQEdadkTsJobXBemhDVdHjXB8Y3gHIpYrslw1YjUbn88q2AqzWZcAwr8B6bEYOO%2F9DxS0qbtm7vV1o3za2lFK0fe5hUDAYBAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&fs_map=eyJpbmRleC50c3giOiJcbmltcG9ydCBkaXA0TW9kZWxVcmwgZnJvbSBcIi4vbW9kZWxzL2RpcDQuZ2xiXCJcblxuZXhwb3J0IGRlZmF1bHQgKCkgPT4gKFxuPGJvYXJkPlxuICA8Y2hpcFxuICAgIG5hbWU9XCJVMVwiXG4gICAgZm9vdHByaW50PVwiZGlwNFwiXG4gICAgY2FkTW9kZWw9ezxjYWRtb2RlbCBtb2RlbFVybD17ZGlwNE1vZGVsVXJsfSAvPn1cbiAgLz5cbjwvYm9hcmQ%2BXG4pXG4iLCIuL21vZGVscy9kaXA0LmdsYiI6Il9fU1RBVElDX0FTU0VUX18ifQ%3D%3D&main_component_path=index.tsx&project_base_url=https%3A%2F%2Fdocs.tscircuit.com%2F)

## Providing a STEP model[​](#providing-a-step-model "Direct link to Providing a STEP model")

You can provide a STEP model to the `<cadmodel />` element by setting the `stepFileUrl`. When providing a STEP model, the STEP model will be used when exporting to STEP to preserve the exact geometry of the model.

> **Example coming soon!**

## Translucent Models[​](#translucent-models "Direct link to Translucent Models")

You can render a component as translucent (semi-transparent) by setting `showAsTranslucentModel` on the component.

```
export default () => (  <board>    <chip      name="U2"      footprint="soic8"      showAsTranslucentModel      cadModel={        <cadmodel          modelUrl="https://modelcdn.tscircuit.com/jscad_models/soic8.glb"        />      }    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA01PwQrCMAy9%2BxWhJ3dZwZPIOvADvLmzdG3nKl1b2gwF8d%2FdYgfmkvdeEvKeecWQELQZ5OwQ9hWIFvY7gKYPMul2QQtWo42EALycjGDdgRU%2BhIAxWY%2BC5WDVcdPzGJ7nfE3SZzcr4%2FEStHFlqKQmKt5FWH9IPf2trEW8S06wETHmE%2BekKO1rzMomNVusVZj4Iy%2FXNxpmTjbqu%2Bs3KwD8lwPgQ51ow0vC6gvjnUEtBAEAAA%3D%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA01PwQrCMAy9%2BxWhJ3dZwZPIOvADvLmzdG3nKl1b2gwF8d%2FdYgfmkvdeEvKeecWQELQZ5OwQ9hWIFvY7gKYPMul2QQtWo42EALycjGDdgRU%2BhIAxWY%2BC5WDVcdPzGJ7nfE3SZzcr4%2FEStHFlqKQmKt5FWH9IPf2trEW8S06wETHmE%2BekKO1rzMomNVusVZj4Iy%2FXNxpmTjbqu%2Bs3KwD8lwPgQ51ow0vC6gvjnUEtBAEAAA%3D%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA01PwQrCMAy9%2BxWhJ3dZwZPIOvADvLmzdG3nKl1b2gwF8d%2FdYgfmkvdeEvKeecWQELQZ5OwQ9hWIFvY7gKYPMul2QQtWo42EALycjGDdgRU%2BhIAxWY%2BC5WDVcdPzGJ7nfE3SZzcr4%2FEStHFlqKQmKt5FWH9IPf2trEW8S06wETHmE%2BekKO1rzMomNVusVZj4Iy%2FXNxpmTjbqu%2Bs3KwD8lwPgQ51ow0vC6gvjnUEtBAEAAA%3D%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA01PwQrCMAy9%2BxWhJ3dZwZPIOvADvLmzdG3nKl1b2gwF8d%2FdYgfmkvdeEvKeecWQELQZ5OwQ9hWIFvY7gKYPMul2QQtWo42EALycjGDdgRU%2BhIAxWY%2BC5WDVcdPzGJ7nfE3SZzcr4%2FEStHFlqKQmKt5FWH9IPf2trEW8S06wETHmE%2BekKO1rzMomNVusVZj4Iy%2FXNxpmTjbqu%2Bs3KwD8lwPgQ51ow0vC6gvjnUEtBAEAAA%3D%3D)

## Supported File Formats[​](#supported-file-formats "Direct link to Supported File Formats")

The following model file formats are supported:

-   GLB
-   GLTF
-   OBJ
-   STEP
-   STL
-   WRL

## Properties[​](#properties "Direct link to Properties")

| Property | Type | Description |
| --- | --- | --- |
| `modelUrl` | `string` | URL to the 3D model file (GLB, GLTF, OBJ, STL, STEP, WRL) |
| `stepUrl` | `string` | URL to a STEP model file for export purposes |
| `positionOffset` | `{x: number, y: number, z: number}` | Offset the model position from the component center |
| `rotationOffset` | `number | {x: number, y: number, z: number}` | Rotate the model (number = Z-axis rotation in degrees) |
| `zOffsetFromSurface` | `Distance` | Vertical offset from the PCB surface (e.g., "2mm", "0.1in") |
| `size` | `{x: number, y: number, z: number}` | Scale the model size |
| `modelUnitToMmScale` | `Distance` | Scale factor to convert model units to millimeters |
