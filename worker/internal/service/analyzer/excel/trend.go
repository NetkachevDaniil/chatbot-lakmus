package excel

import (
	"fmt"
	"github.com/xuri/excelize/v2"
	"sort"
	"strconv"
	"time"
)

type DataPoint struct {
	Date  time.Time
	Value float64
	Group string
}

type TrendAnalyzer struct{}

func NewTrendAnalyzer() *TrendAnalyzer {
	return &TrendAnalyzer{}
}

func (a *TrendAnalyzer) Name() string {
	return "trend"
}

func (a *TrendAnalyzer) RequiredColumns() []string {
	return []string{}
}

func (a *TrendAnalyzer) ValidateParams(params map[string]interface{}) error {
	if _, ok := params["date_column"].(string); !ok {
		return fmt.Errorf("параметр date_column обязателен")
	}
	if _, ok := params["value_column"].(string); !ok {
		return fmt.Errorf("параметр value_column обязателен")
	}
	return nil
}

func (a *TrendAnalyzer) Analyze(f *excelize.File, sheetName string, params map[string]interface{}) (map[string]interface{}, error) {
	if err := a.ValidateParams(params); err != nil {
		return nil, err
	}

	dateColumn := params["date_column"].(string)
	valueColumn := params["value_column"].(string)
	groupBy := ""
	if gb, ok := params["group_by"].(string); ok {
		groupBy = gb
	}

	rows, err := f.GetRows(sheetName)
	if err != nil {
		return nil, fmt.Errorf("не удалось прочитать лист '%s': %w", sheetName, err)
	}

	if len(rows) < 2 {
		return nil, fmt.Errorf("лист '%s' не содержит данных", sheetName)
	}

	headers := rows[0]
	dateIdx := -1
	valueIdx := -1
	groupIdx := -1

	for i, h := range headers {
		if h == dateColumn {
			dateIdx = i
		}
		if h == valueColumn {
			valueIdx = i
		}
		if groupBy != "" && h == groupBy {
			groupIdx = i
		}
	}

	if dateIdx == -1 {
		return nil, fmt.Errorf("колонка даты '%s' не найдена", dateColumn)
	}
	if valueIdx == -1 {
		return nil, fmt.Errorf("колонка значений '%s' не найдена", valueColumn)
	}

	var points []DataPoint

	for i := 1; i < len(rows); i++ {
		row := rows[i]
		if len(row) <= dateIdx || len(row) <= valueIdx {
			continue
		}

		date, err := parseDate(row[dateIdx])
		if err != nil {
			continue
		}

		value, err := strconv.ParseFloat(row[valueIdx], 64)
		if err != nil {
			continue
		}

		group := ""
		if groupIdx != -1 && len(row) > groupIdx {
			group = row[groupIdx]
		}

		points = append(points, DataPoint{Date: date, Value: value, Group: group})
	}

	if len(points) == 0 {
		return nil, fmt.Errorf("нет данных для анализа тренда")
	}

	// Сортируем по дате
	sort.Slice(points, func(i, j int) bool {
		return points[i].Date.Before(points[j].Date)
	})

	result := make(map[string]interface{})

	if groupBy != "" && groupIdx != -1 {
		// Группированный тренд
		groups := make(map[string][]DataPoint)
		for _, p := range points {
			groups[p.Group] = append(groups[p.Group], p)
		}

		trends := make(map[string]interface{})
		for group, groupPoints := range groups {
			trends[group] = calculateTrend(groupPoints)
		}
		result["type"] = "grouped_trend"
		result["sheet"] = sheetName
		result["group_by"] = groupBy
		result["trends"] = trends
	} else {
		// Общий тренд
		result["type"] = "trend"
		result["sheet"] = sheetName
		result["data"] = calculateTrend(points)
	}

	return result, nil
}

func calculateTrend(points []DataPoint) map[string]interface{} {
	if len(points) == 0 {
		return map[string]interface{}{"direction": "no_data"}
	}

	n := len(points)
	firstThird := points[:n/3]
	lastThird := points[2*n/3:]

	avgFirst := 0.0
	for _, p := range firstThird {
		avgFirst += p.Value
	}
	avgFirst /= float64(len(firstThird))

	avgLast := 0.0
	for _, p := range lastThird {
		avgLast += p.Value
	}
	avgLast /= float64(len(lastThird))

	change := avgLast - avgFirst
	changePercent := 0.0
	if avgFirst != 0 {
		changePercent = (change / avgFirst) * 100
	}

	direction := "stable"
	if change > 0.1 {
		direction = "increasing"
	} else if change < -0.1 {
		direction = "decreasing"
	}

	// Берём точки для схемы (не больше 10)
	step := maxFuncInt(1, n/10)
	sampled := make([]map[string]interface{}, 0)
	for i := 0; i < n; i += step {
		sampled = append(sampled, map[string]interface{}{
			"date":  points[i].Date.Format("2006-01-02"),
			"value": points[i].Value,
		})
	}

	return map[string]interface{}{
		"direction":      direction,
		"change":         change,
		"change_percent": changePercent,
		"first_avg":      avgFirst,
		"last_avg":       avgLast,
		"points":         sampled,
		"total_points":   n,
	}
}

func parseDate(s string) (time.Time, error) {
	formats := []string{
		"2006-01-02",
		"02.01.2006",
		"01/02/2006",
		"2006-01-02 15:04:05",
		"02.01.2006 15:04",
		"2006-01-02T15:04:05Z",
	}
	for _, format := range formats {
		if t, err := time.Parse(format, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("не удалось распарсить дату: %s", s)
}

func maxFuncInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
