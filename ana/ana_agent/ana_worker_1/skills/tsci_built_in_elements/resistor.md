# <resistor />

A resistor element has two pins and is non-polar, meaning it doesn't matter if you place it on backwards (it resists electricity identically either way!)

When specifying a resistor, you'll usually want to give it a footprint string such as `0402` or `0603` to indicate it's size. You can see the most popular resistor sizes for different power ratings at [jlcsearch](https://jlcsearch.tscircuit.com/resistors/list)

```ts
export default () => (
<board width="10mm" height="10mm">  
    <resistor    
        name="R1"    
        footprint="0402"    
        resistance="1k"  
    />
</board>)
```


## Pins

| Pin # | Aliases | Description |
| --- | --- | --- |
| pin1 | left, pos | The left side pin in normal orientation |
| pin2 | right, neg | The right side pin in normal orientation |

## Tolerances

Resistors can be made to different tolerances. In particular, you might care about the following resistor characteristics:

-   **tolerance** - a percentage given with a string, e.g. `tolerance="5%"`. This specifies how accurate the resistance needs to be
-   **powerRating** - a wattage e.g. "5W" indicating how much power can transfer through the resistor for normal operation
-   **temperatureOperatingRange** - a string indicating the listed range for the resistor's operating temperature `"-15F-150F"`

