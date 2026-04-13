package analyzer

import (
	"fmt"
	"github.com/xuri/excelize/v2"
	"strconv"
	"strings"
)

type FilterAnalyzer struct{}

func NewFilterAnalyzer() *FilterAnalyzer {
	return &FilterAnalyzer{}
}

func (a *FilterAnalyzer) Name() string {
	return "filter"
}

func (a *FilterAnalyzer) RequiredColumns() []string {
	return []string{}
}

func (a *FilterAnalyzer) ValidateParams(params map[string]interface{}) error {
	if _, ok := params["column"].(string); !ok {
		return fmt.Errorf("параметр column обязателен")
	}
	if _, ok := params["operator"].(string); !ok {
		return fmt.Errorf("параметр operator обязателен")
	}
	if _, ok := params["value"].(string); !ok {
		return fmt.Errorf("параметр value обязателен")
	}

	operator := params["operator"].(string)
	validOperators := map[string]bool{"eq": true, "gt": true, "lt": true, "gte": true, "lte": true, "contains": true}
	if !validOperators[operator] {
		return fmt.Errorf("operator должен быть одним из: eq, gt, lt, gte, lte, contains")
	}
	return nil
}

func (a *FilterAnalyzer) Analyze(f *excelize.File, sheetName string, params map[string]interface{}) (map[string]interface{}, error) {
	if err := a.ValidateParams(params); err != nil {
		return nil, err
	}

	column := params["column"].(string)
	operator := params["operator"].(string)
	value := params["value"].(string)

	returnColumns := make([]string, 0)
	if rc, ok := params["return_columns"].([]interface{}); ok {
		for _, col := range rc {
			if str, ok := col.(string); ok {
				returnColumns = append(returnColumns, str)
			}
		}
	}

	rows, err := f.GetRows(sheetName)
	if err != nil {
		return nil, fmt.Errorf("не удалось прочитать лист '%s': %w", sheetName, err)
	}

	if len(rows) < 2 {
		return nil, fmt.Errorf("лист '%s' не содержит данных", sheetName)
	}

	headers := rows[0]
	filterIdx := -1
	returnIdxs := make([]int, 0)

	for i, h := range headers {
		if h == column {
			filterIdx = i
		}
		for _, rc := range returnColumns {
			if h == rc {
				returnIdxs = append(returnIdxs, i)
			}
		}
	}

	if filterIdx == -1 {
		return nil, fmt.Errorf("колонка '%s' не найдена", column)
	}

	// Если не указаны возвращаемые колонки, возвращаем все
	if len(returnIdxs) == 0 {
		for i := range headers {
			returnIdxs = append(returnIdxs, i)
		}
	}

	var results []map[string]interface{}

	for i := 1; i < len(rows); i++ {
		row := rows[i]
		if len(row) <= filterIdx {
			continue
		}

		cellValue := row[filterIdx]
		match := false

		switch operator {
		case "eq":
			match = cellValue == value
		case "contains":
			match = strings.Contains(strings.ToLower(cellValue), strings.ToLower(value))
		case "gt":
			num, err := strconv.ParseFloat(cellValue, 64)
			val, _ := strconv.ParseFloat(value, 64)
			match = err == nil && num > val
		case "lt":
			num, err := strconv.ParseFloat(cellValue, 64)
			val, _ := strconv.ParseFloat(value, 64)
			match = err == nil && num < val
		case "gte":
			num, err := strconv.ParseFloat(cellValue, 64)
			val, _ := strconv.ParseFloat(value, 64)
			match = err == nil && num >= val
		case "lte":
			num, err := strconv.ParseFloat(cellValue, 64)
			val, _ := strconv.ParseFloat(value, 64)
			match = err == nil && num <= val
		}

		if match {
			rowResult := make(map[string]interface{})
			for _, idx := range returnIdxs {
				if idx < len(row) {
					rowResult[headers[idx]] = row[idx]
				} else {
					rowResult[headers[idx]] = nil
				}
			}
			results = append(results, rowResult)
		}
	}

	return map[string]interface{}{
		"type":     "filter",
		"sheet":    sheetName,
		"column":   column,
		"operator": operator,
		"value":    value,
		"matched":  len(results),
		"results":  results[:min(20, len(results))],
	}, nil
}
