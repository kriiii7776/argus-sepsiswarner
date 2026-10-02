/// Formats a model probability for display without rounding small positive
/// risks down to zero.
String formatRiskPercentage(double? probability) {
  if (probability == null || !probability.isFinite || probability < 0 || probability > 1) {
    return 'Risk unavailable';
  }
  final percentage = probability * 100;
  if (percentage > 0 && percentage < 0.01) return '<0.01%';
  return '${percentage.toStringAsFixed(2)}%';
}
