import datetime

from django.core.urlresolvers import reverse
from django.http import JsonResponse

from django.views.generic import View, ListView
from django.db.models import Sum
from .models import Transaction, Category


def get_month_transaction_queryset(year, month):
    start = datetime.date(year, month, 1)
    if month == 12:
        end = datetime.date(year + 1, 1, 1)
    else:
        end = datetime.date(year, month + 1, 1)

    return Transaction.objects.filter(date__gte=start, date__lt=end)


class HomeView(ListView):
    model = Transaction
    template_name = 'home.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        today = datetime.date.today()
        month = int(self.request.GET.get('month', today.month))
        year = int(self.request.GET.get('year', today.year))
        return get_month_transaction_queryset(year, month).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        month = int(self.request.GET.get('month', today.month))
        year = int(self.request.GET.get('year', today.year))
        last_year_start = datetime.date(year - 1, 1, 1)
        next_year_start = datetime.date(year + 1, 1, 1)

        months = []
        for month_num in range(12):
            month_start = datetime.date(year, month_num + 1, 1)
            months.append((month_start, month_start > today))

        context['transaction_timeline'] = {
            'previous_year': (year - 1, last_year_start > today),
            'next_year': (year + 1, next_year_start > today),
            'current_month': month,
            'months': months
        }

        context['in_out_data_url'] = reverse('transactions:in_out_data', args=[year, month])

        return context


class IncomingOutgoingDataView(View):
    def get(self, request, year, month):
        transaction_qs = get_month_transaction_queryset(int(year), int(month))

        def process_in_out_qs(qs):
            return dict(qs.values('category').annotate(total=Sum('amount')).values_list('category', 'total'))

        in_qs, out_qs = transaction_qs.filter(amount__gt=0), transaction_qs.filter(amount__lt=0)
        in_category_amount_map, out_category_amount_map = map(process_in_out_qs, [in_qs, out_qs])

        categories = list(Category.objects.values_list('pk', flat=True))

        in_data = ['Incoming']
        out_data = ['Outgoing']

        for category in [None] + categories:
            in_data.append(float(in_category_amount_map.get(category, 0)))
            out_data.append(-float(out_category_amount_map.get(category, 0)))

        in_data.append(float(in_qs.aggregate(total=Sum('amount'))['total']))
        out_data.append(-float(out_qs.aggregate(total=Sum('amount'))['total']))

        return JsonResponse({
            'data': [
                ['Category', 'Uncategorised'] + categories + [{'role': 'annotation'}],
                in_data,
                out_data
            ],
            'options': {
                'isStacked': True,
                'legend': {
                    'position': 'top'
                },
                'backgroundColor': 'transparent'
            }
        })
