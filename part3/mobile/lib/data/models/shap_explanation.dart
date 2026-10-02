class ShapContribution {
  final String feature;
  final double? value;
  final double attributionLogOdds;
  final String direction;
  final String description;

  ShapContribution({
    required this.feature,
    this.value,
    required this.attributionLogOdds,
    required this.direction,
    required this.description,
  });

  factory ShapContribution.fromJson(Map<String, dynamic> json) {
    final feat = json['feature_name']?.toString() ??
        json['feature']?.toString() ??
        'unknown';
    final val = (json['feature_value'] is num)
        ? (json['feature_value'] as num).toDouble()
        : ((json['value'] is num) ? (json['value'] as num).toDouble() : null);
    final attrLogOdds = (json['shap_value'] is num)
        ? (json['shap_value'] as num).toDouble()
        : ((json['attribution_log_odds'] is num)
            ? (json['attribution_log_odds'] as num).toDouble()
            : 0.0);
    final dir = json['contribution_direction']?.toString() ??
        json['direction']?.toString() ??
        'unknown';
    final desc = json['description']?.toString() ?? '';

    return ShapContribution(
      feature: feat,
      value: val,
      attributionLogOdds: attrLogOdds,
      direction: dir,
      description: desc,
    );
  }
}

class ShapExplanation {
  final bool explanationAvailable;
  final String? reason;
  final String? outputSpace;
  final double? baseValueLogOdds;
  final double? explainedOutputLogOdds;
  final List<ShapContribution> featureAttributions;
  final List<ShapContribution> topContributions;
  final String? modelVersion;

  ShapExplanation({
    required this.explanationAvailable,
    this.reason,
    this.outputSpace,
    this.baseValueLogOdds,
    this.explainedOutputLogOdds,
    required this.featureAttributions,
    required this.topContributions,
    this.modelVersion,
  });

  factory ShapExplanation.fromJson(Map<String, dynamic> json) {
    final attributionsList = (json['feature_attributions'] as List<dynamic>?)
            ?.map((e) => ShapContribution.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];
    final topList = (json['top_contributions'] as List<dynamic>?)
            ?.map((e) => ShapContribution.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];

    return ShapExplanation(
      explanationAvailable: json['explanation_available'] == true,
      reason: json['reason']?.toString(),
      outputSpace: json['output_space']?.toString(),
      baseValueLogOdds: (json['base_value_log_odds'] is num)
          ? (json['base_value_log_odds'] as num).toDouble()
          : null,
      explainedOutputLogOdds: (json['explained_output_log_odds'] is num)
          ? (json['explained_output_log_odds'] as num).toDouble()
          : null,
      featureAttributions: attributionsList,
      topContributions: topList,
      modelVersion: json['model_version']?.toString(),
    );
  }
}
