package analyzer

import (
	"fmt"
	"github.com/xuri/excelize/v2"
	"math"
	"strconv"
)

type CorrelationAnalyzer struct{}

func NewCorrelationAnalyzer() *CorrelationAnalyzer {
	return &CorrelationAnalyzer{}
}

func (a *CorrelationAnalyzer) Name() string {
	return "correlation"
}

func (a *CorrelationAnalyzer) RequiredColumns() []string {
	return []string{}
}

func (a *CorrelationAnalyzer) ValidateParams(params map[string]interface{}) error {
	if _, ok := params["column_x"].(string); !ok {
		return fmt.Errorf("параметр column_x обязателен")
	}
	if _, ok := params["column_y"].(string); !ok {
		return fmt.Errorf("параметр column_y обязателен")
	}
	return nil
}

func (a *CorrelationAnalyzer) Analyze(f *excelize.File, sheetName string, params map[string]interface{}) (map[string]interface{}, error) {
	if err := a.ValidateParams(params); err != nil {
		return nil, err
	}

	columnX := params["column_x"].(string)
	columnY := params["column_y"].(string)

	rows, err := f.GetRows(sheetName)
	if err != nil {
		return nil, fmt.Errorf("не удалось прочитать лист '%s': %w", sheetName, err)
	}

	if len(rows) < 2 {
		return nil, fmt.Errorf("лист '%s' не содержит данных", sheetName)
	}

	headers := rows[0]
	idxX := -1
	idxY := -1

	for i, h := range headers {
		if h == columnX {
			idxX = i
		}
		if h == columnY {
			idxY = i
		}
	}

	if idxX == -1 {
		return nil, fmt.Errorf("колонка '%s' не найдена", columnX)
	}
	if idxY == -1 {
		return nil, fmt.Errorf("колонка '%s' не найдена", columnY)
	}

	var valuesX, valuesY []float64

	for i := 1; i < len(rows); i++ {
		row := rows[i]
		if len(row) <= idxX || len(row) <= idxY {
			continue
		}

		valX, errX := strconv.ParseFloat(row[idxX], 64)
		valY, errY := strconv.ParseFloat(row[idxY], 64)

		if errX == nil && errY == nil {
			valuesX = append(valuesX, valX)
			valuesY = append(valuesY, valY)
		}
	}

	if len(valuesX) < 2 {
		return nil, fmt.Errorf("недостаточно данных для корреляции (минимум 2 пары значений)")
	}

	correlation := pearsonCorrelation(valuesX, valuesY)
	strength := getCorrelationStrength(correlation)

	// Интерпретация
	interpretation := ""
	if correlation > 0 {
		interpretation = "положительная"
	} else if correlation < 0 {
		interpretation = "отрицательная"
	} else {
		interpretation = "отсутствует"
	}

	return map[string]interface{}{
		"type":           "correlation",
		"sheet":          sheetName,
		"column_x":       columnX,
		"column_y":       columnY,
		"correlation":    correlation,
		"strength":       strength,
		"interpretation": interpretation,
		"sample_size":    len(valuesX),
	}, nil
}

func pearsonCorrelation(x, y []float64) float64 {
	n := float64(len(x))
	sumX, sumY, sumXY := 0.0, 0.0, 0.0
	sumX2, sumY2 := 0.0, 0.0

	for i := 0; i < len(x); i++ {
		sumX += x[i]
		sumY += y[i]
		sumXY += x[i] * y[i]
		sumX2 += x[i] * x[i]
		sumY2 += y[i] * y[i]
	}

	numerator := sumXY - (sumX * sumY / n)
	denominator := math.Sqrt((sumX2 - sumX*sumX/n) * (sumY2 - sumY*sumY/n))

	if denominator == 0 {
		return 0
	}
	return numerator / denominator
}

func getCorrelationStrength(r float64) string {
	absR := math.Abs(r)
	switch {
	case absR >= 0.7:
		return "strong"
	case absR >= 0.3:
		return "moderate"
	default:
		return "weak"
	}
}
