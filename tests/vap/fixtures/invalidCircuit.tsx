// Invalid circuit with deterministic errors (missing required props)
export default () => {
    return (
        <board width="10mm" height="10mm">
            {/* Missing required 'name' prop - will cause evaluation error */}
            <resistor resistance="1k" footprint="0402" schX={0} schY={0} />
            {/* Invalid trace reference - nonexistent component */}
            <trace from=".NonExistent > .pin1" to=".AlsoMissing > .pin2" />
        </board>
    )
}
