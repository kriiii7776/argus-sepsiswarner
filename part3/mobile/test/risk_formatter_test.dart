import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/core/utils/risk_formatter.dart';

void main() {
  test('keeps ordinary risks precise', () {
    expect(formatRiskPercentage(0.862403), '86.24%');
  });

  test('does not round small positive risks down to zero', () {
    expect(formatRiskPercentage(0.00012569325996341176), '0.01%');
    expect(formatRiskPercentage(0.000001), '<0.01%');
  });

  test('formats zero and unavailable values safely', () {
    expect(formatRiskPercentage(0), '0.00%');
    expect(formatRiskPercentage(null), 'Risk unavailable');
    expect(formatRiskPercentage(double.nan), 'Risk unavailable');
    expect(formatRiskPercentage(1.01), 'Risk unavailable');
  });
}
