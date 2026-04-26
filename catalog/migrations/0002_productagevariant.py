from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductAgeVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('age_years', models.PositiveSmallIntegerField(verbose_name='Возраст (лет)')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена')),
                ('stock', models.PositiveIntegerField(default=100, verbose_name='Остаток')),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='age_variants',
                    to='catalog.product',
                    verbose_name='Товар',
                )),
            ],
            options={
                'verbose_name': 'Возрастной вариант',
                'verbose_name_plural': 'Возрастные варианты',
                'ordering': ['age_years'],
                'unique_together': {('product', 'age_years')},
            },
        ),
    ]
