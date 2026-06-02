export type CheckStatus = 'pass' | 'fail' | 'warning' | 'skipped'

export interface FieldCheck {
  field_name: string
  expected: string
  found?: string | null
  status: CheckStatus
  message: string
  confidence: number
}

export interface VerificationResult {
  filename: string
  overall_status: CheckStatus
  checks: FieldCheck[]
  extracted_text: string
  processing_time_ms: number
  image_preview?: string | null
}

export interface BatchVerificationResponse {
  results: VerificationResult[]
  total: number
  passed: number
  failed: number
  warnings: number
  total_processing_time_ms: number
}

export interface ApplicationData {
  brand_name: string
  class_type: string
  alcohol_content: string
  net_contents: string
  government_warning: string
  bottler_producer: string
  country_of_origin: string
}

export const STANDARD_WARNING =
  'GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.'

export const EMPTY_APPLICATION: ApplicationData = {
  brand_name: '',
  class_type: '',
  alcohol_content: '',
  net_contents: '',
  government_warning: STANDARD_WARNING,
  bottler_producer: '',
  country_of_origin: '',
}
