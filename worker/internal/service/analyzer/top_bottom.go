package analyzer

import (
	"fmt"
	"github.com/xuri/excelize/v2"
	"sort"
	"strconv"
)

type TopBottomAnalyzer struct{}

func NewTopBottomAnalyzer() *TopBottomAnalyzer {
	return &TopBottomAnalyzer{}
}

func (a *TopBottomAnalyzer) Name() string {
	return "top_bottom"
}

func (a *TopBottomAnalyzer) RequiredColumns() []string {
	return []string{}
}

func (a *TopBottomAnalyzer) ValidateParams(params map[string]interface{}) error {
	if _, ok := params["name_column"].(string); !ok {
		return fmt.Errorf("параметр name_column обязателен")
	}
	if _, ok := params["value_column"].(string); !ok {
		return fmt.Errorf("параметр value_column обязателен")
	}
	if _, ok := params["mode"].(string); !ok {
		return fmt.Errorf("параметр mode обязателен (top или bottom)")
	}
	mode := params["mode"].(string)
	if mode != "top" && mode != "bottom" {
		return fmt.Errorf("mode должен быть 'top' или 'bottom'")
	}
	return nil
}

func (a *TopBottomAnalyzer) Analyze(f *excelize.File, sheetName string, params map[string]interface{}) (map[string]interface{}, error) {
	if err := a.ValidateParams(params); err != nil {
		return nil, err
	}

	nameColumn := params["name_column"].(string)
	valueColumn := params["value_column"].(string)
	mode := params["mode"].(string)

	limit := 5
	if l, ok := params["limit"].(float64); ok {
		limit = int(l)
	}

	rows, err := f.GetRows(sheetName)
	if err != nil {
		return nil, fmt.Errorf("не удалось прочитать лист '%s': %w", sheetName, err)
	}

	if len(rows) < 2 {
		return nil, fmt.Errorf("лист '%s' не содержит данных", sheetName)
	}

	headers := rows[0]
	nameIdx := -1
	valueIdx := -1

	for i, h := range headers {
		if h == nameColumn {
			nameIdx = i
		}
		if h == valueColumn {
			valueIdx = i
		}
	}

	if nameIdx == -1 {
		return nil, fmt.Errorf("колонка '%s' не найдена", nameColumn)
	}
	if valueIdx == -1 {
		return nil, fmt.Errorf("колонка '%s' не найдена", valueColumn)
	}

	type Item struct {
		Name  string
		Value float64
	}

	var items []Item

	for i := 1; i < len(rows); i++ {
		row := rows[i]
		if len(row) <= nameIdx || len(row) <= valueIdx {
			continue
		}

		name := row[nameIdx]
		if name == "" {
			continue
		}

		value, err := strconv.ParseFloat(row[valueIdx], 64)
		if err != nil {
			continue
		}

		items = append(items, Item{Name: name, Value: value})
	}

	if len(items) == 0 {
		return nil, fmt.Errorf("нет числовых данных в колонке '%s'", valueColumn)
	}

	// Сортируем
	if mode == "top" {
		sort.Slice(items, func(i, j int) bool {
			return items[i].Value > items[j].Value
		})
	} else {
		sort.Slice(items, func(i, j int) bool {
			return items[i].Value < items[j].Value
		})
	}

	// Берём limit
	if len(items) > limit {
		items = items[:limit]
	}

	result := make(map[string]interface{})
	for _, item := range items {
		result[item.Name] = item.Value
	}

	return map[string]interface{}{
		"type":  "top_bottom",
		"sheet": sheetName,
		"mode":  mode,
		"limit": limit,
		"data":  result,
	}, nil
}
