# Plugin: vout_spipoti

Variable-Output using digital poti with SPI Interface (like MCP413X/415X/423X/425X)

```
{
    "type": "vout_spipoti",
    "bits": "8",
    "speed": "1000000",
    "pins": {
        "MOSI": "A1",
        "SCLK": "A3",
        "CS": "A4"
    }
},
```

https://cdn-reichelt.de/documents/datenblatt/A200/MCP4151_MIC.pdf

# vout_spipoti.v
![graphviz](./vout_spipoti.svg)

