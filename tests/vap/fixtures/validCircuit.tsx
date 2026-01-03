// Valid circuit that should evaluate successfully
export default () => {
  return (
    <board width="10mm" height="10mm">
      <resistor name="R1" resistance="1k" footprint="0402" schX={0} schY={0} />
      <capacitor name="C1" capacitance="100nF" footprint="0402" schX={5} schY={0} />
      <trace from=".R1 > .pin2" to=".C1 > .pin1" />
    </board>
  )
}
