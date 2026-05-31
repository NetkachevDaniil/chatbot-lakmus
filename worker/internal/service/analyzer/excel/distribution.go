package excel

import (
	"fmt"
	"github.com/xuri/excelize/v2"
	"math"
	"sort"
	"strconv"
)

type DistributionAnalyzer struct{}

func NewDistributionAnalyzer() *DistributionAnalyzer {
	return &DistributionAnalyzer{}
}

func (a *DistributionAnalyzer) Name() string {
	return "distribution"
}

func (a *DistributionAnalyzer) RequiredColumns() []string {
	return []string{}
}

func (a *DistributionAnalyzer) ValidateParams(params map[string]interface{}) error {
	if _, ok := params["value_column"].(string); !ok {
		return fmt.Errorf("параметр value_column обязателен")
	}
	return nil
}

func (a *DistributionAnalyzer) Analyze(f *excelize.File, sheetName string, params map[string]interface{}) (map[string]interface{}, error) {
	if err := a.ValidateParams(params); err != nil {
		return nil, err
	}

	valueColumn := params["value_column"].(string)
	bins := 5
	if b, ok := params["bins"].(float64); ok {
		bins = int(b)
	}

	rows, err := f.GetRows(sheetName)
	if err != nil {
		return nil, fmt.Errorf("не удалось прочитать лист '%s': %w", sheetName, err)
	}

	if len(rows) < 2 {
		return nil, fmt.Errorf("лист '%s' не содержит данных", sheetName)
	}

	headers := rows[0]
	valueIdx := -1

	for i, h := range headers {
		if h == valueColumn {
			valueIdx = i
		}
	}

	if valueIdx == -1 {
		return nil, fmt.Errorf("колонка '%s' не найдена", valueColumn)
	}

	var values []float64

	for i := 1; i < len(rows); i++ {
		row := rows[i]
		if len(row) <= valueIdx {
			continue
		}

		val, err := strconv.ParseFloat(row[valueIdx], 64)
		if err == nil {
			values = append(values, val)
		}
	}

	if len(values) == 0 {
		return nil, fmt.Errorf("нет числовых данных в колонке '%s'", valueColumn)
	}

	sort.Float64s(values)

	minVal := values[0]
	maxVal := values[len(values)-1]
	binWidth := (maxVal - minVal) / float64(bins)

	histogram := make([]int, bins)
	for _, v := range values {
		idx := int((v - minVal) / binWidth)
		if idx >= bins {
			idx = bins - 1
		}
		if idx < 0 {
			idx = 0
		}
		histogram[idx]++
	}

	// Статистика
	meanVal := mean(values)
	medianVal := median(values)
	stdDev := standardDeviation(values, meanVal)

	// Процентили
	p25 := percentile(values, 25)
	p75 := percentile(values, 75)

	// Построение интервалов для гистограммы
	binEdges := make([]string, bins+1)
	for i := 0; i <= bins; i++ {
		edge := minVal + float64(i)*binWidth
		binEdges[i] = fmt.Sprintf("%.1f", edge)
	}

	return map[string]interface{}{
		"type":      "distribution",
		"sheet":     sheetName,
		"column":    valueColumn,
		"count":     len(values),
		"min":       minVal,
		"max":       maxVal,
		"mean":      meanVal,
		"median":    medianVal,
		"std_dev":   stdDev,
		"p25":       p25,
		"p75":       p75,
		"histogram": histogram,
		"bin_edges": binEdges,
	}, nil
}

func median(values []float64) float64 {
	n := len(values)
	if n == 0 {
		return 0
	}
	if n%2 == 0 {
		return (values[n/2-1] + values[n/2]) / 2
	}
	return values[n/2]
}

func standardDeviation(values []float64, meanVal float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sumSq := 0.0
	for _, v := range values {
		sumSq += (v - meanVal) * (v - meanVal)
	}
	return math.Sqrt(sumSq / float64(len(values)))
}

func percentile(values []float64, p float64) float64 {
	if len(values) == 0 {
		return 0
	}
	idx := (p / 100) * float64(len(values)-1)
	lower := int(math.Floor(idx))
	upper := int(math.Ceil(idx))
	if lower == upper {
		return values[lower]
	}
	return values[lower] + (values[upper]-values[lower])*(idx-float64(lower))
}
