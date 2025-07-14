from django import forms
from .models import AnonymousSubmission
from mapwidgets.widgets import LeafletPointFieldWidget

class AnonymousMemorialForm(forms.ModelForm):
    cc0_agree = forms.BooleanField(
        required=True,
        label="Strinjam se z morebitno objavo podatkov pod licenco CC0 (javna last)",
    )
    class Meta:
        model = AnonymousSubmission
        fields = [
            'name', 'description', 'geom', 'memorial_access', 'memorial_text', 'memorial_author',
            'memorial_start', 'status', 'entry_author', 'cc0_agree',
        ]
        widgets = {
            'geom': LeafletPointFieldWidget(),  # Use django-map-widgets LeafletPointWidget for interactive point selection
            'description': forms.Textarea(attrs={'rows': 3}),
            'memorial_text': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
            'changes': forms.Textarea(attrs={'rows': 2}),
        }
