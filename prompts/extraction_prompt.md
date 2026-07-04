Extract phospholipid-regulated protein evidence from the article below.

Use only the title and abstract. Do not use external knowledge. Do not invent identifiers, protein accessions, lipid IDs, PDB IDs, organisms, methods, or mechanisms. If a field is not explicitly supported, use null. Keep summaries short and faithful to the source text.

Return JSON only. The top-level value must be an array. Each array item must represent one protein-phospholipid regulation evidence record. If the title and abstract do not contain explicit evidence for a phospholipid regulating a protein, return [].

Required output fields for each record:
- protein_name_reported
- protein_name_standard
- gene_symbol
- uniprot_id
- organism
- protein_type
- physiological_function
- lipid_name_reported
- lipid_name_standard
- lipid_class
- headgroup
- phosphorylation_position
- acyl_chain_if_reported
- regulation_relationship
- direct_or_indirect
- effect_direction
- functional_effect
- mechanism_summary
- cellular_context
- membrane_compartment
- site_resolution_level
- binding_domain
- residue_reported
- lipid_moiety_bound
- lipid_headgroup_detail
- mutation_tested
- mutation_effect
- membrane_localization_type
- subcellular_location
- lipid_dependency
- localization_evidence
- disease_name
- is_lipid_regulation_related
- figure_or_table
- original_evidence_sentence
- experimental_method
- quantitative_value
- evidence_level
- review_status
- llm_confidence
- ambiguity_flag
- curator_note

Controlled values:
- regulation_relationship: direct_binding, membrane_recruitment, activation, inhibition, gating, conformational_change, stabilization, complex_assembly, membrane_partitioning, membrane_property_mediated, binding_only, unknown
- direct_or_indirect: direct, indirect, unclear, unknown
- effect_direction: activation, inhibition, recruitment, stabilization, destabilization, gating, binding_only, unknown
- site_resolution_level: atomic_structure, mutagenesis_supported, domain_level, lipid_species_only, predicted, unknown
- membrane_localization_type: integral_transmembrane, peripheral_lipid_binding, lipid_binding_domain_mediated, lipidation_mediated, electrostatic_patch_mediated, amphipathic_helix_mediated, raft_partitioning, unknown
- evidence_level: A, B, C, D, E, unknown
- review_status: pending

Evidence level guide:
- A: direct binding + functional change + site/mutation/structure evidence
- B: direct binding + functional change
- C: localization or function affected, but direct binding is not proven
- D: binding evidence only, without clear functional regulation
- E: prediction, review statement, or domain inference only
- unknown: not enough information in title/abstract

Article:
PMID: {pmid}
Title: {title}
Journal: {journal}
Year: {year}
DOI: {doi}
Abstract: {abstract}
