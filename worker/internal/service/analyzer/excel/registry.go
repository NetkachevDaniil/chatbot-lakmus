package excel

import (
	"example.com/bot_worker/internal/service"
)

type Registry struct {
	analyzers map[string]service.Analyzer
}

func NewRegistry() *Registry {
	r := &Registry{
		analyzers: make(map[string]service.Analyzer),
	}

	r.Register(NewGroupComparisonAnalyzer())
	r.Register(NewTopBottomAnalyzer())
	r.Register(NewCorrelationAnalyzer())
	r.Register(NewTrendAnalyzer())
	r.Register(NewDistributionAnalyzer())
	r.Register(NewFilterAnalyzer())

	return r
}

func (r *Registry) Register(a service.Analyzer) {
	r.analyzers[a.Name()] = a
}

func (r *Registry) Get(name string) (service.Analyzer, bool) {
	a, ok := r.analyzers[name]
	return a, ok
}

func (r *Registry) List() []string {
	names := make([]string, 0, len(r.analyzers))
	for name := range r.analyzers {
		names = append(names, name)
	}
	return names
}
