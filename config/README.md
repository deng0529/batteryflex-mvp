# BatteryFlex configuration

Version-controlled defaults ship with the Python package under
[`src/batteryflex/resources`](../src/batteryflex/resources/).

| File | Authority |
| --- | --- |
| [app.yaml](../src/batteryflex/resources/app.yaml) | Product identity, displayed version and Overview precision. |
| [portfolio.yaml](../src/batteryflex/resources/portfolio.yaml) | Ordered residential assets, common battery limits and efficiencies, configured initial state of charge and standard experiment event-start SoCs. |
| [simulation.yaml](../src/batteryflex/resources/simulation.yaml) | Experiment A mode, default kW obligation, tariffs, objective weights, reserve, terminal target and MPC solver settings. |
| [forecasting.yaml](../src/batteryflex/resources/forecasting.yaml) | Dispatch forecast priority and explicit event model UI inputs. |
| [neso_selection_v1.json](../src/batteryflex/resources/neso_selection_v1.json) | Reviewed historical event registry, original source records and integrity hashes. |
| [.streamlit/config.toml](../.streamlit/config.toml) | Native Streamlit theme and viewer settings. |

Use the JSON syntax shown in each YAML file. It is the safely parsed JSON subset of YAML 1.2
and adds no parser dependency. The loader rejects duplicate keys, missing fields, invalid ranges
and unsupported settings. Startup checks the event intervals against the reviewed source windows.
Restart Streamlit after editing version-controlled defaults.

The event source registry stays in its existing hashed format. The historical mapping function,
30-minute protocol, forecast schemas, estimator fallbacks and legacy full-day model defaults
remain versioned in Python so old records can be rehydrated with the original semantics.

Working portfolio edits and runtime dispatch overrides never edit these files. Explicit
portfolio saves create a new immutable version when persistent storage is connected.
A dispatch result records effective numerical inputs, exact forecast and source references,
and the controller protocol. Display changes are outside numerical identity.

Configure deployment secrets through environment variables or a private project-local
`.env` using [the example](../.env.example). The application default is dedicated Turso and
Cloudflare R2. Set `BATTERYFLEX_STORAGE_MODE=local` for an explicitly bootstrapped local store.
[Storage configuration](../docs/STORAGE.md)
