{{ name | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ fullname }}

{% block methods %}

{% if methods %}
.. rubric:: {{ _('Methods') }}

.. autosummary::
   :toctree:
   :template: only_names_in_toc.rst
{% for item in methods %}
   ~{{ name }}.{{ item }}
{%- endfor %}
{% endif %}
{% endblock %}

{% block attributes %}
{% if attributes %}
.. rubric:: {{ _('Attributes') }}

.. autosummary::
   :toctree:
   :template: only_names_in_toc.rst
{% for item in attributes %}
   ~{{ name }}.{{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
