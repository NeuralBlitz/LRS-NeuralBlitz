export interface CKInfo {
    name: string;
    family: string;
    version: string;
    intent: string;
    inputs: Record<string, string>;
    outputs: Record<string, string>;
    riskFactors: string[];
    veritasInvariants: string[];
    governance: {
        rcf: boolean;
        cect: boolean;
        veritasWatch: boolean;
        judexQuorum: boolean;
    };
}

export class CKRegistry {
    private static instance: CKRegistry;
    private cks: Map<string, CKInfo> = new Map();
    private families: Set<string> = new Set();

    constructor() {
        if (CKRegistry.instance) {
            return CKRegistry.instance;
        }
        CKRegistry.instance = this;
        this.initializeDefaultCKs();
    }

    private initializeDefaultCKs(): void {
        // Causa Suite
        this.registerCK({
            name: 'CounterfactualPlannerCK',
            family: 'Causa',
            version: '1.2.0',
            intent: 'Generates and ranks plans under "what-if" causal scenarios',
            inputs: {
                goals: 'Array of goal objects',
                world_model: 'CID of world model',
                options: 'Array of plan options'
            },
            outputs: {
                ranked_plans: 'CID of ranked plans',
                regret_bounds: 'Array of regret bounds',
                uncertainty: 'Uncertainty quantification'
            },
            riskFactors: ['Spurious Causality', 'Unidentified Confounders'],
            veritasInvariants: ['VPROOF#FlourishMonotone', 'VPROOF#CausalConsistency'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'CausalGraphInducerCK',
            family: 'Causa',
            version: '1.0.1',
            intent: 'Infers causal DAGs from event streams or narratives',
            inputs: {
                event_stream_cid: 'Content identifier',
                temporal_range: 'Time range specification'
            },
            outputs: {
                causal_graph: 'CID of causal graph'
            },
            riskFactors: ['Confounding Bias'],
            veritasInvariants: ['VPROOF#BiasBoundedness', 'VPROOF#ProvenanceIntegrity'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'BackdoorFinderCK',
            family: 'Causa',
            version: '1.1.0',
            intent: 'Discovers minimal blocking sets to control backdoor paths',
            inputs: {
                causal_graph: 'CID of causal graph',
                treatment: 'Treatment variable CID',
                outcome: 'Outcome variable CID'
            },
            outputs: {
                blocking_sets_Zstar: 'Array of blocking sets'
            },
            riskFactors: ['Set Minimality Failure'],
            veritasInvariants: ['VPROOF#MinimalityZstar'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        // Ethics Suite
        this.registerCK({
            name: 'MetaEthicalSolverCK',
            family: 'Ethics',
            version: '1.3.0',
            intent: 'Reconciles conflicts between multiple ethical principles',
            inputs: {
                ethical_dilemma: 'CID of dilemma description',
                principles_weighted: 'Array of weighted principles'
            },
            outputs: {
                stance: 'CID of resolved stance',
                tradeoff_table: 'CID of tradeoff analysis',
                rationale: 'CID of justification'
            },
            riskFactors: ['Value Smuggling'],
            veritasInvariants: ['VPROOF#ValueImpartiality', 'VPROOF#ExplainabilityCoverage'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'HarmBoundEstimatorCK',
            family: 'Ethics',
            version: '1.1.0',
            intent: 'Computes upper bounds on potential harm',
            inputs: {
                action_plan: 'CID of plan to evaluate',
                harm_metrics: 'Array of harm metrics'
            },
            outputs: {
                H_max: 'Maximum harm bound',
                confidence: 'Confidence level'
            },
            riskFactors: ['Underestimation of Harm'],
            veritasInvariants: ['VPROOF#MinimaxHarm', 'VPROOF#RobustHarmEstimation'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'FairnessFrontierCK',
            family: 'Ethics',
            version: '1.0.0',
            intent: 'Generates Pareto optimal frontiers across fairness metrics',
            inputs: {
                stakeholders: 'Array of stakeholder groups',
                fairness_metrics: 'Array of fairness metrics'
            },
            outputs: {
                frontier_solutions: 'CID of frontier solutions',
                pivot_points: 'Array of pivot points'
            },
            riskFactors: ['Fairness Unachievability'],
            veritasInvariants: ['VPROOF#FairnessTradeoffIden'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'ConsentVerifierCK',
            family: 'Ethics',
            version: '1.0.0',
            intent: 'Verifies adherence to consent preconditions',
            inputs: {
                user_consent_record_cid: 'Consent record CID',
                action_cid: 'Action CID'
            },
            outputs: {
                consent_status: 'CID of status',
                missing_preconditions: 'Array of missing items'
            },
            riskFactors: ['Privacy Breach'],
            veritasInvariants: ['VPROOF#ConsentAdherence'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        // Wisdom Synthesis Suite
        this.registerCK({
            name: 'WisdomSynthesisCF',
            family: 'Wisdom',
            version: '1.2.0',
            intent: 'Synthesizes optimal choices by distilling trade-offs',
            inputs: {
                options: 'Array of options',
                metrics_scores: 'Object with metric scores'
            },
            outputs: {
                wise_choice: 'CID of optimal choice',
                justification: 'CID of justification',
                confidence: 'Confidence score'
            },
            riskFactors: ['Suboptimal Synthesis'],
            veritasInvariants: ['VPROOF#FlourishOptimal'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'LongHorizonReasonerCK',
            family: 'Wisdom',
            version: '1.0.0',
            intent: 'Generates policy paths with long-term ethical weight',
            inputs: {
                policy_options: 'Array of policy options',
                discount_rate_model: 'CID of discount model',
                ethical_weights: 'Array of ethical weights'
            },
            outputs: {
                horizon_policy: 'CID of policy',
                impact_projections: 'CID of projections'
            },
            riskFactors: ['Intergenerational Harm'],
            veritasInvariants: ['VPROOF#TemporalEquity'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'RegretBounderCK',
            family: 'Wisdom',
            version: '1.0.0',
            intent: 'Computes and minimizes minimax regret',
            inputs: {
                decision_options: 'Array of options',
                scenario_set_cid: 'CID of scenarios',
                loss_function: 'CID of loss function'
            },
            outputs: {
                minimax_choice: 'CID of optimal choice',
                bound_certificate: 'CID of bound certificate'
            },
            riskFactors: ['Regret Misestimation'],
            veritasInvariants: ['VPROOF#RegretMinimality'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'NarrativeBridgerCK',
            family: 'Wisdom',
            version: '0.9.0',
            intent: 'Transforms technical outputs into public narratives',
            inputs: {
                technical_report_cid: 'CID of technical report',
                audience_profile: 'CID of audience profile'
            },
            outputs: {
                public_narrative_cid: 'CID of public narrative'
            },
            riskFactors: ['Meaning Distortion'],
            veritasInvariants: ['VPROOF#MeaningPreservation'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        // OQT-BOS Suite
        this.registerCK({
            name: 'TensorKnotGateCK',
            family: 'OQT',
            version: '1.0.2',
            intent: 'Executes topological/quantum gate operations on braids',
            inputs: {
                braid_id: 'Braid CID',
                op_type: 'Operation type (PHASE, CNOT, NON_LOCAL_REWRITE)',
                params: 'Operation parameters',
                qec_guard: 'Enable QEC guarding'
            },
            outputs: {
                braid_id: 'Result braid CID',
                qec_syndrome: 'QEC syndrome',
                psi_delta: 'Phase delta'
            },
            riskFactors: ['QEC Breach', 'Unbounded Topological Rewrite'],
            veritasInvariants: ['VPROOF#QECInvariant', 'VPROOF#BraidHomotopy'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: true
            }
        });

        this.registerCK({
            name: 'InvariantMeasurerCK',
            family: 'OQT',
            version: '1.0.0',
            intent: 'Measures topological invariants of braids',
            inputs: {
                braid_id: 'Braid CID'
            },
            outputs: {
                invariant_report: 'CID of invariant report'
            },
            riskFactors: ['Miscalculation'],
            veritasInvariants: ['VPROOF#TopologicalTruth'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: false
            }
        });

        this.registerCK({
            name: 'TeletopoCourierCK',
            family: 'OQT',
            version: '0.8.0',
            intent: 'Executes cross-instance entanglement',
            inputs: {
                braid_id: 'Braid CID',
                destination_instance_uri: 'Destination URI',
                Judex_quorum_stamp_cid: 'Quorum stamp CID'
            },
            outputs: {
                transfer_receipt: 'CID of receipt'
            },
            riskFactors: ['Unauthorized Transfer'],
            veritasInvariants: ['VPROOF#JudexApproval', 'VPROOF#SecureChannel'],
            governance: {
                rcf: true,
                cect: true,
                veritasWatch: true,
                judexQuorum: true
            }
        });
    }

    registerCK(ck: CKInfo): void {
        const key = `${ck.family}/${ck.name}`;
        this.cks.set(key, ck);
        this.families.add(ck.family);
    }

    async getFamilies(): Promise<string[]> {
        return Array.from(this.families).sort();
    }

    async getCKsInFamily(family: string): Promise<CKInfo[]> {
        const result: CKInfo[] = [];
        for (const ck of this.cks.values()) {
            if (ck.family === family) {
                result.push(ck);
            }
        }
        return result.sort((a, b) => a.name.localeCompare(b.name));
    }

    async getCK(family: string, name: string): Promise<CKInfo | undefined> {
        return this.cks.get(`${family}/${name}`);
    }

    async getFamilyDescription(family: string): Promise<string> {
        const descriptions: Record<string, string> = {
            'Causa': 'Causal inference and counterfactual analysis capabilities',
            'Ethics': 'Meta-ethical reasoning and value alignment systems',
            'Wisdom': 'Holistic reasoning and long-term value synthesis',
            'Temporal': 'Time, prediction, and evolutionary modeling',
            'Language': 'Meaning, narrative, and communication processing',
            'Perception': 'Information verification and safety systems',
            'Simulation': 'Scenario generation and mechanism design',
            'OQT': 'Octa-Topological Braided OS operations',
            'DQPK': 'Dynamic Quantum Plasticity Kernels',
            'DRS': 'Dynamic Representational Substrate operations',
            'Plan': 'Strategic foresight and decision making',
            'Gov': 'Governance, safety, and explainability systems'
        };
        return descriptions[family] || `${family} Capability Kernel family`;
    }

    async search(query: string): Promise<CKInfo[]> {
        const results: CKInfo[] = [];
        const lowerQuery = query.toLowerCase();
        
        for (const ck of this.cks.values()) {
            if (
                ck.name.toLowerCase().includes(lowerQuery) ||
                ck.intent.toLowerCase().includes(lowerQuery) ||
                ck.family.toLowerCase().includes(lowerQuery)
            ) {
                results.push(ck);
            }
        }
        
        return results;
    }
}