/**
 * Compatibility surface for callers that still use the former results-view name.
 * The implementation lives exclusively in SmearAnalysisImmersiveView.
 */
export {
  SmearAnalysisImmersiveView,
  SmearAnalysisImmersiveView as SmearAnalysisResultsView,
} from './SmearAnalysisImmersiveView';

export type {
  SmearAnalysisActions,
  SmearAnalysisHistoryViewProps,
  SmearAnalysisImmersiveViewProps,
  SmearAnalysisLiveViewProps,
  SmearAnalysisPermissions,
  SmearAnalysisResultsViewProps,
  SmearAnalysisViewMode,
  SmearAnalysisViewModel,
} from './SmearAnalysisImmersiveView';
