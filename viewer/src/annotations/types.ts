export type AnnotationCategory = 'correction' | 'insight' | 'feedback' | 'commendation' | 'question';

export interface RangeSelector {
  blockIndex: number;
  quote: string;
  prefixContext: string;
  suffixContext: string;
  textOffsetInBlock: number;
  startContainerPath?: string;
  endContainerPath?: string;
  startOffset?: number;
  endOffset?: number;
}

export interface DocumentAnnotation {
  id: string;
  createdAt: string;
  updatedAt?: string;
  author: string;
  category: AnnotationCategory;
  text: string;
  range: RangeSelector;
  resolved: boolean;
  tags?: string[];
  orphaned?: boolean;
}

export interface AnnotationsManifest {
  version: string;
  author?: string;
  updated_at?: string;
  annotations: DocumentAnnotation[];
}
