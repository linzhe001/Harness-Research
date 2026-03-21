# Release Checklist

## Validate

For each target scene:

- required checkpoint exists
- all expected outputs are rendered
- filenames match competition rules
- image format is correct
- image resolution is correct

## Package

- render test outputs with the locked eval entry script
- organize the expected submission directory layout
- include `submission/README.md`
- create an archive only after validation succeeds

## Submit

- use the best config or explicitly chosen config
- record which checkpoint was used for each scene
- do not overwrite an existing package without confirmation
