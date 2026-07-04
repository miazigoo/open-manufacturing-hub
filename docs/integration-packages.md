# Integration Packages

OMH Core is the runtime. Integration Packages provide ecosystem-specific experience.

A package can provide:

- connectors;
- execution steps;
- resolver presets;
- transformation presets;
- business object presets;
- scenario presets;
- operation templates;
- mapping presets;
- frontend navigation metadata;
- package docs;
- demo data installers.

Stable extension points:

- Connector SDK;
- Execution Step SDK;
- Resolver SDK;
- Transformation SDK;
- Business Object SDK;
- Frontend Navigation metadata;
- Scenario Preset Installer;
- Operation Template Installer;
- Mapping Preset Installer.

Official MVP packages:

- `omh-package-onec`: 1C connector, OData/XML tools, Workbench, scenario presets and visual flow presets.
- `omh-package-printer`: ZPL printer connector, printing UI and print operation step.

Future package slots:

- SAP;
- Odoo;
- Shopify;
- MQTT;
- RabbitMQ;
- MES/WMS;
- EDI;
- barcode/GS1 systems.
