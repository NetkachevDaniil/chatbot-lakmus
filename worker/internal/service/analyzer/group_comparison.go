package analyzer

import (
	"fmt"
	"github.com/xuri/excelize/v2"
	"strconv"
)

type GroupComparisonAnalyzer struct{}

func NewGroupComparisonAnalyzer() *GroupComparisonAnalyzer {
	return &GroupComparisonAnalyzer{}
}

func (a *GroupComparisonAnalyzer) Name() string {
	return "group_comparison"
}

func (a *GroupComparisonAnalyzer) RequiredColumns() []string {
	return []string{}
}

func (a *GroupComparisonAnalyzer) ValidateParams(params map[string]interface{}) error {
	if _, ok := params["group_column"].(string); !ok {
		return fmt.Errorf("параметр group_column обязателен и должен быть строкой")
	}
	if _, ok := params["value_column"].(string); !ok {
		return fmt.Errorf("параметр value_column обязателен и должен быть строкой")
	}
	return nil
}

func (a *GroupComparisonAnalyzer) Analyze(f *excelize.File, sheetName string, params map[string]interface{}) (map[string]interface{}, error) {
	if err := a.ValidateParams(params); err != nil {
		return nil, err
	}

	groupColumn := params["group_column"].(string)
	valueColumn := params["value_column"].(string)

	aggregation := "mean"
	if agg, ok := params["aggregation"].(string); ok {
		aggregation = agg
	}

	// Читаем указанный лист
	rows, err := f.GetRows(sheetName)
	if err != nil {
		return nil, fmt.Errorf("не удалось прочитать лист '%s': %w", sheetName, err)
	}

	if len(rows) < 2 {
		return nil, fmt.Errorf("лист '%s' не содержит данных", sheetName)
	}

	headers := rows[0]
	groupIdx := -1
	valueIdx := -1

	for i, h := range headers {
		if h == groupColumn {
			groupIdx = i
		}
		if h == valueColumn {
			valueIdx = i
		}
	}

	if groupIdx == -1 {
		return nil, fmt.Errorf("колонка '%s' не найдена на листе '%s'", groupColumn, sheetName)
	}
	if valueIdx == -1 {
		return nil, fmt.Errorf("колонка '%s' не найдена на листе '%s'", valueColumn, sheetName)
	}

	// Группируем данные
	groups := make(map[string][]float64)

	for i := 1; i < len(rows); i++ {
		row := rows[i]
		if len(row) <= groupIdx || len(row) <= valueIdx {
			continue
		}

		groupKey := row[groupIdx]
		if groupKey == "" {
			continue
		}

		value, err := strconv.ParseFloat(row[valueIdx], 64)
		if err != nil {
			continue
		}

		groups[groupKey] = append(groups[groupKey], value)
	}

	if len(groups) == 0 {
		return nil, fmt.Errorf("нет данных для группировки")
	}

	// Агрегируем
	result := make(map[string]interface{})
	for group, values := range groups {
		switch aggregation {
		case "mean":
			result[group] = mean(values)
		case "sum":
			result[group] = sumFunc(values)
		case "count":
			result[group] = float64(len(values))
		case "min":
			result[group] = minFunc(values)
		case "max":
			result[group] = maxFuncSlice(values)
		default:
			result[group] = mean(values)
		}
	}

	return map[string]interface{}{
		"type":        "group_comparison",
		"sheet":       sheetName,
		"group_by":    groupColumn,
		"metric":      valueColumn,
		"aggregation": aggregation,
		"data":        result,
	}, nil
}

func mean(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sm := 0.0
	for _, v := range values {
		sm += v
	}
	return sm / float64(len(values))
}

func sumFunc(values []float64) float64 {
	sm := 0.0
	for _, v := range values {
		sm += v
	}
	return sm
}

func minFunc(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	m := values[0]
	for _, v := range values {
		if v < m {
			m = v
		}
	}
	return m
}

func maxFuncSlice(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	m := values[0]
	for _, v := range values {
		if v > m {
			m = v
		}
	}
	return m
}
