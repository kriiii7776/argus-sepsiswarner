import 'package:flutter/material.dart';
import '../../core/constants/app_theme.dart';
import '../../data/models/shap_explanation.dart';

class ShapContributorsView extends StatelessWidget {
  final ShapExplanation? explanation;

  const ShapContributorsView({super.key, this.explanation});

  @override
  Widget build(BuildContext context) {
    if (explanation == null || !explanation!.explanationAvailable) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          explanation?.reason ?? 'SHAP model contributor attributions unavailable.',
          style: const TextStyle(fontSize: 12, color: Colors.white54),
        ),
      );
    }

    final topList = explanation!.topContributions.isNotEmpty
        ? explanation!.topContributions
        : explanation!.featureAttributions.take(5).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.analytics_outlined, size: 16, color: Colors.blueAccent),
            SizedBox(width: 6),
            Expanded(
              child: Text(
                'Model Contributors (Log-Odds Impact)',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        const Text(
          'Factors contributed to the model risk score; they do not imply biological causation.',
          style: TextStyle(fontSize: 11, color: Colors.white54, fontStyle: FontStyle.italic),
        ),
        const SizedBox(height: 10),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: topList.length,
          separatorBuilder: (_, __) => const SizedBox(height: 6),
          itemBuilder: (context, index) {
            final c = topList[index];
            final isIncrease = c.attributionLogOdds > 0 ||
                c.direction == 'increases_risk' ||
                c.direction == 'positive';
            final impactColor = isIncrease ? AppColors.redUrgent : AppColors.greenNormal;
            final signStr = c.attributionLogOdds >= 0 ? '+' : '';
            final valStr = '$signStr${c.attributionLogOdds.toStringAsFixed(3)}';

            final featName = c.description.isNotEmpty ? c.description : c.feature;
            final valText = c.value != null ? ' (${c.value!.toStringAsFixed(1)})' : '';

            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.04),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: impactColor.withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      '$featName$valText',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                      overflow: TextOverflow.ellipsis,
                      maxLines: 2,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: impactColor.withValues(alpha: 0.18),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: impactColor.withValues(alpha: 0.4)),
                    ),
                    child: Text(
                      valStr,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: impactColor,
                      ),
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}
