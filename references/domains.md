# Domain adapters

Choose a domain only when it changes source authority, version handling, or protocol routing. `domain-registry.json` is the source of truth used by both the runtime and this guide.

Available adapters:

- `AI_AGENTS`, `SOFTWARE`, `META_ADS`, and `ECOMMERCE` are version-sensitive; record product/API/model version and prefer official documentation, release notes, source code, reproducible tests, or account-level experiments as appropriate.
- `LAW` always adds `LEGAL_AUTHORITY`; preserve jurisdiction, authority hierarchy, effective date, operative text, and exceptions.
- `HISTORY` adds `HISTORICAL_SOURCE_CRITICISM`; distinguish event attestation from historical explanation and preserve temporal distance and source dependence.
- `MEDICINE_HEALTH` separates guidelines, treatment effects, mechanisms, and anecdotes; population, dose, outcome, and harms remain in scope.
- `FINANCE_INVESTING` preserves benchmark, fees, window, asset class, and the difference between historical distribution and a guarantee.
- `NATURAL_SCIENCE` preserves operational definitions, units, measurement protocol, and boundary conditions.
- `SOCIAL_SCIENCE_ECONOMICS` preserves construct definitions, identification strategy, geography, and time.
- `EDUCATION_PSYCHOLOGY` separates preferences and anecdotes from intervention efficacy.
- `FOOD_COOKING` separates safety rules, observed effects, preferences, and folk mechanisms.
- `SPORTS` preserves league, season, metric definition, and model scope.

Source kinds are exact machine labels. A preferred kind may support admission; an explicitly insufficient kind cannot be the sole support; an unlisted kind produces `HOLD` until classified. `SOFTWARE`, `META_ADS`, `LAW`, `MEDICINE_HEALTH`, and `FINANCE_INVESTING` also provide optional claim-class-specific rules. If `claim_class` is supplied, it must match a class registered for the selected domain. The registry includes generic source kinds for claims without a domain.

Adapters do not decide truth and do not expand the user's requested source boundary.
