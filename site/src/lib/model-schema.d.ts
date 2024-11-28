/* eslint-disable */
/**
 * This file was automatically generated by json-schema-to-typescript.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source JSONSchema file,
 * and run json-schema-to-typescript to regenerate this file.
 */

export interface ModelMetadata {
  model_name: string
  model_key?: string
  model_version: string
  matbench_discovery_version: string
  date_added: string
  date_published: string
  authors: {
    name: string
    affiliation?: string
    email?: string
    orcid?: string
    [k: string]: unknown
  }[]
  trained_by?: {
    name: string
    affiliation?: string
    orcid?: string
    github?: string
    [k: string]: unknown
  }[]
  repo: string
  doi: string
  paper: string
  url?: string
  pypi?: string
  requirements: {
    /**
     * This interface was referenced by `undefined`'s JSON-Schema definition
     * via the `patternProperty` "^[a-zA-Z]{1}[a-zA-Z0-9_\-]{0,}$".
     */
    [k: string]: string
  }
  trained_for_benchmark: boolean
  training_set: (
    | 'MP 2022'
    | 'MPtrj'
    | 'MPF'
    | 'MP Graphs'
    | 'GNoME'
    | 'MatterSim'
    | 'Alex'
    | 'OMat24'
    | 'sAlex'
  )[]
  hyperparams?: {
    max_force?: number
    max_steps?: number
    optimizer?: string
    ase_optimizer?: string
    learning_rate?: number
    batch_size?: number
    epochs?: number
    n_layers?: number
    radial_cutoff?: number
    [k: string]: unknown
  }
  notes?: {
    Description?: string
    Training?: string
    'Missing Preds'?: string
    html?: {
      [k: string]: unknown
    }
    [k: string]: unknown
  }
  model_params: number
  n_estimators: number
  train_task: 'RP2RE' | 'RS2RE' | 'S2E' | 'S2RE' | 'S2EF' | 'S2EFS' | 'S2EFSM'
  test_task: 'IP2E' | 'IS2E' | 'IS2RE' | 'IS2RE-SR' | 'IS2RE-BO'
  model_type: 'GNN' | 'UIP' | 'BO-GNN' | 'Fingerprint' | 'Transformer' | 'RF'
  targets: 'E' | 'EF_G' | 'EF_D' | 'EFS_G' | 'EFS_D' | 'EFS_GM' | 'EFS_DM'
  openness?: 'OSOD' | 'OSCD' | 'CSOD' | 'CSCD'
  status?: 'aborted' | 'complete'
  metrics?: {
    phonons?:
      | {
          κ_SRME?: number
        }
      | ('not applicable' | 'not available')
    geo_opt?:
      | {
          pred_file: string | null
          pred_col: string | null
          rmsd?: number
          n_sym_ops_mae?: number
          symmetry_decrease?: number
          symmetry_match?: number
          symmetry_increase?: number
          n_structures?: number
        }
      | ('not applicable' | 'not available')
    discovery?: {
      additionalProperties?: never
      pred_file?: string
      pred_col?: string
      full_test_set?: {
        F1?: number
        DAF?: number
        Precision?: number
        Recall?: number
        Accuracy?: number
        TPR?: number
        FPR?: number
        TNR?: number
        FNR?: number
        TP?: number
        FP?: number
        TN?: number
        FN?: number
        MAE?: number
        RMSE?: number
        R2?: number
        missing_preds?: number
        missing_percent?: string
      }
      most_stable_10k?: {
        F1?: number
        DAF?: number
        Precision?: number
        Recall?: number
        Accuracy?: number
        TPR?: number
        FPR?: number
        TNR?: number
        FNR?: number
        TP?: number
        FP?: number
        TN?: number
        FN?: number
        MAE?: number
        RMSE?: number
        R2?: number
        missing_preds?: number
        missing_percent?: string
      }
      unique_prototypes?: {
        F1?: number
        DAF?: number
        Precision?: number
        Recall?: number
        Accuracy?: number
        TPR?: number
        FPR?: number
        TNR?: number
        FNR?: number
        TP?: number
        FP?: number
        TN?: number
        FN?: number
        MAE?: number
        RMSE?: number
        R2?: number
        missing_preds?: number
        missing_percent?: string
      }
    }
  }
}
