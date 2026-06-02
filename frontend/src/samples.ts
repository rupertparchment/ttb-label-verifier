import type { ApplicationData } from './types'
import { STANDARD_WARNING } from './types'

export interface SamplePreset {
  id: string
  label: string
  filename: string
  expected: 'pass' | 'fail'
  application: ApplicationData
}

export const SAMPLE_PRESETS: SamplePreset[] = [
  {
    id: 'old_tom',
    label: 'Old Tom Distillery (pass)',
    filename: 'old_tom_distillery_pass.png',
    expected: 'pass',
    application: {
      brand_name: 'OLD TOM DISTILLERY',
      class_type: 'Kentucky Straight Bourbon Whiskey',
      alcohol_content: '45% Alc./Vol. (90 Proof)',
      net_contents: '750 mL',
      government_warning: STANDARD_WARNING,
      bottler_producer: 'Old Tom Distillery, Louisville, KY',
      country_of_origin: '',
    },
  },
  {
    id: 'stones_throw',
    label: "Stone's Throw — fuzzy brand (pass)",
    filename: 'stones_throw_fuzzy_pass.png',
    expected: 'pass',
    application: {
      brand_name: "Stone's Throw",
      class_type: 'Small Batch Gin',
      alcohol_content: '44% Alc./Vol.',
      net_contents: '750 mL',
      government_warning: STANDARD_WARNING,
      bottler_producer: "Stone's Throw Spirits, Portland, OR",
      country_of_origin: '',
    },
  },
  {
    id: 'glenmore',
    label: 'Glenmore Highland — import (pass)',
    filename: 'glenmore_import_pass.png',
    expected: 'pass',
    application: {
      brand_name: 'GLENMORE HIGHLAND',
      class_type: 'Blended Scotch Whisky',
      alcohol_content: '40% Alc./Vol. (80 Proof)',
      net_contents: '1 L',
      government_warning: STANDARD_WARNING,
      bottler_producer: 'Imported by Atlantic Spirits Co., Baltimore, MD',
      country_of_origin: 'Product of Scotland',
    },
  },
  {
    id: 'bad_warning',
    label: 'Riverside Vodka — bad warning (fail)',
    filename: 'bad_warning_fail.png',
    expected: 'fail',
    application: {
      brand_name: 'Riverside Vodka',
      class_type: 'Premium Vodka',
      alcohol_content: '40% Alc./Vol. (80 Proof)',
      net_contents: '1 L',
      government_warning: STANDARD_WARNING,
      bottler_producer: 'Riverside Distilling Co.',
      country_of_origin: '',
    },
  },
  {
    id: 'abv_mismatch',
    label: 'Mountain Peak Rye — ABV mismatch (fail)',
    filename: 'abv_mismatch_fail.png',
    expected: 'fail',
    application: {
      brand_name: 'Mountain Peak Rye',
      class_type: 'Straight Rye Whiskey',
      alcohol_content: '46% Alc./Vol.',
      net_contents: '750 mL',
      government_warning: STANDARD_WARNING,
      bottler_producer: 'Mountain Peak Distillery',
      country_of_origin: '',
    },
  },
]
