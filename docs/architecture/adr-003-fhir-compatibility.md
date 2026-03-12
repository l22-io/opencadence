# ADR-003: FHIR R4 Compatibility Layer

## Status
Accepted

## Context
Healthcare interoperability standards (HL7 FHIR) enable data exchange with clinical systems. However, FHIR's data model is optimized for clinical workflows, not time-series storage and querying.

## Decision
Keep the internal data model optimized for time-series operations. Provide a read-only FHIR R4 export layer that maps internal samples to FHIR Observation resources on-the-fly. No FHIR write path.

## Alternatives Considered
- **FHIR-native storage**: Store all data as FHIR resources. High interoperability but poor query performance for time-series use cases and unnecessary complexity for self-hosters.
- **No FHIR support**: Simpler, but closes the door to clinical system integration.

## Consequences
- Internal queries remain fast (native time-series model)
- FHIR export available for systems that need it
- Mapping maintained per metric type in YAML registry
- No SMART on FHIR scopes for MVP (standard JWT auth)
